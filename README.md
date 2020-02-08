# uMeta (micro metadata)

Index your files.

## Concepts

* Namespace: a group in which all bucket names are unique.  umeta has only 1 global namespace, so all buckets across all sources must be unique.
* Source: a named backend.

## Environment Config

| variable     | default                    | description                |
|--------------|----------------------------|----------------------------|
| CONFIG_PATH  | 'config/umeta.config.json' | path to configuration file |
| DATABASE_URI | 'sqlite:///test.db'        | postgres database URI      |
