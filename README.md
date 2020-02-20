![uMeta Logo](docs/micrometa.png)

uMeta generates indexes and derived data (like thumbnails).  It runs alongside **s3** or **minio** because the world already has enough filesystem abstractions.  uMeta is not a fileserver.

## Concepts

Micrometa (uMeta) is a tool for building and managing derivative data like exif tags, thumbnails, and search indexes.

It uses **s3** or **minio** for storage and **elasticsearch** for index curation.

Its core philosophies are:

* Don't reinvent the wheel. s3, minio, and elasticsearch are already perfect.
* Data freedom first. Not all data interactions will happen through uMeta.  That's OK.
* Data flexibility next.  uMeta comes to your data.  You don't bring your data to it.
* Low-cost abandonment.  Decide you hate uMeta?  You should be able to throw away your indices and move on to the next thing without complicated "export" procedures.


## Alternatives

* Nextcloud.  Nextcloud doesn't like when you modify things directly on disk, it's slow, and upgrades are painful and often result in a broken deployment.
* filestash.app.  Filestash is rigid, and generates derived data like thumbnails on the fly.  This is a waste of time and bandwidth for slow-moving data archives, particularly when there isn't a fat pipe between the filestash deployment and your data.  It also provides yet another abstraction over already abstract filesystems.  Search is buggy.

## Environment Config

| variable     | default                    | description                |
|--------------|----------------------------|----------------------------|
| CONFIG_PATH  | 'config/umeta.config.json' | path to configuration file |
| DATABASE_URI | 'sqlite:///test.db'        | postgres database URI      |
