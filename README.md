# Gavel

A fork for Reality Hack, Inc.

## Status

This is a fork of the original Gavel repo, refactored to suit the purposes of the Reality Hack, Inc organization, adding more context for simpler installation procedures and removing the implied hard requirement of using Postgres. Reality Hack, Inc claims no ownership over the original derived materials and maintains the original commit history.

## Configuration

1. Copy configuration template:

```shell
cp config.template.yaml config.yaml
```

2. Configure the database URI for SQLite3 in `config.yaml`:

```yaml
db_uri: sqlite:///db.sqlite3
```

The file will live in `gavel/db.sqlite3`.

3. Note regarding the `admin_password` and `secret_key` entries in `config.yaml`:

- If these fields are only numbers, they will not work for some reason.

4. Configure any remaining variables in `config.yaml`.

## Run

**This was tested in a clean Python `3.10.13` virtual environment.**

### Install dependencies

1. Install Python dependencies:

```shell
pip install -r requirements.txt
```

2. Email-sending relies on a running installation of Redis (`redis-server`).

### Initialize Database

```shell
./initialize.py
```

### Run Server

#### In Development Mode

```shell
./runserver.py
```

#### In Production

The following example is for illustrative purposes only. It assumes a clone in the `/root` directory of a deployed service.

1. Create a `systemd` service for the Gavel app at `/etc/systemd/system/gavel.service`:

```ini
[Unit]
Description=Gavel daemon for Flask app
Before=nginx.service
After=network.target

[Service]
WorkingDirectory=/root/gavel
ExecStart=gunicorn -b :8000 gavel:app
Restart=always
SyslogIdentifier=gavel
User=root
Group=root

[Install]
WantedBy=multi-user.target
```

2. Similarly to above, a service should be created for `celery` to be able to run async tasks relating to sending emails at `/etc/systemd/system/celery.service`:

```ini
[Unit]
Description=Celery daemon for Gavel
Before=nginx.service
After=network.target

[Service]
WorkingDirectory=/root/gavel
ExecStart=celery -A gavel:celery worker
Restart=always
SyslogIdentifier=celery
User=root
Group=root

[Install]
WantedBy=multi-user.target

```

3. The above example would then be started by running the following:

  - Only once, ever:
```shell
systemctl enable gavel
systemctl enable celery
# This will automatically start the services on system boot, but does not start it immedately, so the next command must be run:
```
  - When the service should be started, if not already started:
```shell
systemctl start gavel
systemctl start celery
# or stop or restart
```

## Usage

### Admin

Log into the admin interface found at `/admin` on your deployment and enter the credentials as follows:

- `Username`: "admin"
- `Password`: The value of `admin_password` from `config.yaml`

To set up the system, use the admin interface on `/admin`. Log in with the
username `admin` and the password you set. Once you're logged in, you can input
information for all the projects and judges.

- Judges will automatically get email invitations as they are added.
- The judging and ranking process is fully automated
- The admin panel will rank projects in real time, ordered by their inferred quality (Mu).
- Judging can be stopped by clicking the "CLOSE" button at the bottom of the page.
  - Judging can be subsequently resumed by clicking "OPEN"
  button under "Global Settings"
- Emails can be force-resent by clicking the "EMAIL" button next to a Judge entry.
- Judges can be give a login link and asked to proceed to `/login/<secret>` on your deployment.
- An available Judge can be sent to a project immediately by clicking the "PRIORITIZE" button next to a Project entry.
- Judges or Projects can be disabled or deleted at any time by clicking "DISABLE" or "DELETE," respectively next to a related entry.
- Details for a given Project or Judge can be inspected by clicking the related clickable ID on the far left of each related entry.

### Judge

- The Judge will receive a "magic link" email, allowing them to auth and commence judging.
- The Judge will be able to read the welcome text, then begin judging.

## Citation

If you use Gavel in any way in academic work, please cite the following:

```bibtex
@misc{athalye2016gavel,
  author = {Anish Athalye},
  title = {Gavel},
  year = {2016},
  howpublished = {\url{https://github.com/anishathalye/gavel}},
}
```

## License

Copyright (c) Anish Athalye. Released under AGPLv3. See
[LICENSE.txt][license] for details.

[blog-1]: http://www.anishathalye.com/2015/03/07/designing-a-better-judging-system/
[blog-2]: http://www.anishathalye.com/2015/11/09/implementing-a-scalable-judging-system/
[issues]: https://github.com/anishathalye/gavel/issues
[contributing]: CONTRIBUTING.md
[license]: LICENSE.txt
[development]: DEVELOPMENT.md
[email]: mailto:me@anishathalye.com
[gunicorn]: http://gunicorn.org/
[users]: https://github.com/anishathalye/gavel/wiki/Users
