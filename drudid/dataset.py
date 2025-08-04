"""
Dataset management module for the drudid project.

This module provides CLI commands for fetching, merging, and converting
Drupal.org API data. It handles paginated data retrieval, JSON processing,
and conversion to various formats like CSV and Parquet.
"""

import gc
import glob
import time

import httpx
from loguru import logger
import orjson
import pandas as pd
from tqdm import tqdm
import typer

from drudid.config import (
    DEV_MODE,
    FETCHER_BASE_PARAMS,
    FETCHER_BASE_URL,
    INTERIM_DATA_DIR,
    RAW_DATA_DIR,
)
from drudid.fetcher import Fetcher

app = typer.Typer()


def load_large_csv_to_pd(input_file: str, chunk_size: int = typer.Option(1000)) -> pd.DataFrame:
    """
    Load a large CSV file into a pandas DataFrame using chunked reading.

    This function reads a CSV file in chunks to manage memory usage,
    ensuring all data is converted to strings to handle mixed data types.

    Args:
        input_file: Path to the input CSV file
        chunk_size: Number of rows to read per chunk for memory management

    Returns:
        pd.DataFrame: Combined DataFrame with all data as strings
    """
    chunk_list = []
    for chunk in pd.read_csv(
        input_file,
        low_memory=False,
        chunksize=chunk_size,
        on_bad_lines="skip",
        dtype=str,  # Force all columns to be read as strings
    ):
        # Convert everything to string, handling all edge cases
        for col in chunk.columns:
            chunk[col] = chunk[col].apply(lambda x: str(x) if pd.notna(x) else "")

        chunk_list.append(chunk)

    return pd.concat(chunk_list, ignore_index=True)


@app.command()
def pull(
    start_page: int = typer.Option(0, help="Starting page (default: 1)"),
    end_page: int = typer.Option(None, help="Ending page (default: None)"),
    force: bool = typer.Option(False, "--force", "-f", help="Refetch even if file exists"),
):
    """
    Source external data from Drupal.org API.

    This function save paginated results as JSON files locally.
    """
    params = FETCHER_BASE_PARAMS
    logger.info(f"Retrieving data from {FETCHER_BASE_URL}")

    fetcher = Fetcher()
    dataset_dir = RAW_DATA_DIR
    dataset_dir.mkdir(parents=True, exist_ok=True)

    if end_page is not None:
        if end_page <= start_page:
            logger.error("End page must be greater than start page")
            return
    else:
        # Only apply DEV_MODE limitation when end_page is not explicitly set
        if DEV_MODE:
            end_page = start_page + 1
        else:
            end_page = fetcher.get_total_pages(params)

    total_pages = end_page - start_page
    logger.info(f"Total {total_pages} pages to process")

    for i in tqdm(range(start_page, end_page), total=total_pages):
        file_path = dataset_dir / f"page_{i}.json"
        if file_path.exists() and not force:
            logger.info(f"Skipping page {i} (use --force to overwrite).")
            continue

        params["page"] = str(i)

        # Sleep to avoid hitting the rate limit too quickly.
        time.sleep(1)

        response = fetcher.fetch_data(params)
        if isinstance(response, httpx.Response):
            with open(file_path, "wb") as f:
                f.write(orjson.dumps(response.json()))
                logger.success(f"Page {i} saved to {file_path}")


@app.command()
def merge(
    chunk_size: int = typer.Option(1000, help="Number of files to process at once"),
):
    """
    Merge multiple JSON files into a single CSV file.

    This function processes JSON files from the raw data directory,
    extracts data from each file, and combines them into a single
    CSV file for further processing. Files are processed in chunks
    to manage memory usage.

    Args:
        chunk_size: Number of files to process simultaneously
    """
    logger.info(f"Merging dataset (chunk size: {chunk_size})")

    files = glob.glob(str(RAW_DATA_DIR / "*.json"))
    total_files = len(files)
    logger.info(f"Found {total_files} files to merge")

    if not files:
        logger.warning("No files found to merge")
        return

    output_file = INTERIM_DATA_DIR / "merged.csv"
    first_chunk = True
    total_rows = 0

    # Process files in chunks to manage memory
    for chunk_start in tqdm(range(0, total_files, chunk_size), desc="Processing chunks"):
        chunk_files = files[chunk_start : chunk_start + chunk_size]
        chunk_dataframes = []

        # Process current chunk
        for file in chunk_files:
            try:
                with open(file, "rb") as f:
                    items = orjson.loads(f.read())
                    if "list" in items:
                        items = items["list"]
                    else:
                        logger.warning(f"Unexpected JSON structure in {file}")
                        continue

                    if items:
                        df = pd.DataFrame(items)
                        chunk_dataframes.append(df)

            except Exception as e:
                logger.error(f"Error processing {file}: {e}")
                continue

        # Process current chunk if we have data
        if chunk_dataframes:
            chunk_df = pd.concat(chunk_dataframes, ignore_index=True)
            total_rows += len(chunk_df)

            # Write to CSV (append mode after first chunk)
            if first_chunk:
                chunk_df.to_csv(output_file, index=False, mode="w")
                first_chunk = False
                logger.info(f"Created output file with {len(chunk_df)} rows")
            else:
                chunk_df.to_csv(output_file, index=False, mode="a", header=False)
                logger.info(f"Appended {len(chunk_df)} rows (total: {total_rows})")

            # Clear memory
            del chunk_df
            del chunk_dataframes

        # Force garbage collection after each chunk
        gc.collect()

    logger.success(f"Merged dataset saved to {output_file} with {total_rows} total rows")


@app.command()
def convert(
    chunk_size: int = typer.Option(1000, help="Number of rows per chunk for processing"),
):
    """
    Convert merged CSV dataset to Parquet format.

    This function loads the merged CSV file created by the merge command
    and converts it to Parquet format for more efficient storage and
    querying. All data is normalized to string format before conversion.

    Args:
        chunk_size: Number of rows to process per chunk during CSV loading
    """
    input_dataset_dir = INTERIM_DATA_DIR
    input_dataset_dir.mkdir(parents=True, exist_ok=True)
    output_dataset_dir = RAW_DATA_DIR
    output_dataset_dir.mkdir(parents=True, exist_ok=True)

    try:
        logger.info("Converting dataset to Parquet format")
        df = load_large_csv_to_pd(str(input_dataset_dir / "merged.csv"), chunk_size=chunk_size)
        logger.info(f"Successfully loaded {len(df)} rows")

        # Safety check.
        logger.debug("Converting all columns to string")
        for col in df.columns:
            try:
                df[col] = df[col].astype(str)
            except Exception as e:
                logger.warning(f"Issue converting column '{col}': {e}")
                df[col] = df[col].apply(lambda x: str(x) if x is not None else "")

        # Save to parquet file.
        try:
            df.to_parquet(
                output_dataset_dir / "merged.parquet",
                index=False,
                engine="pyarrow",
                compression="snappy",
            )
            logger.success("Dataset converted to parquet")
        except (ImportError, ValueError, OSError) as parquet_error:
            logger.error(f"Parquet conversion error: {parquet_error}")
            # Try with different engine or settings
            df.to_parquet(
                output_dataset_dir / "merged.parquet",
                index=False,
                engine="pyarrow",
                compression=None,
                use_deprecated_int96_timestamps=True,
            )
            logger.success("Dataset converted to parquet with fallback settings")

    except Exception as e:
        logger.error(f"Conversion failed: {e}")


if __name__ == "__main__":
    app()
