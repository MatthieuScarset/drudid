# drudid documentation!

## Description

A machine learning system to automatically detect and flag potential duplicate issues on Drupal.org.

## Commands

The Makefile contains the central entry points for common tasks related to this project.

### Syncing data to cloud storage

* `make sync_data_up` will use `gsutil rsync` to recursively sync files in `data/` up to `gs://drudid/data/`.
* `make sync_data_down` will use `gsutil rsync` to recursively sync files in `gs://drudid/data/` to `data/`.


