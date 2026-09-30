# OSHF Kerko Library

This repository runs the [Open Science Hardware Library](https://library.opensciencehardware.org), a public bibliography built from the OSHF Zotero group library with [KerkoApp](https://github.com/whiskyechobravo/kerkoapp). It contains the Kerko configuration, OSHF templates and static assets, a cover-image builder, and the Docker Compose stack that serves the site.

## Contents

- [Services](#services)
- [Configuration](#configuration)
- [How it works](#how-it-works)
- [Running locally](#running-locally)

Reference documentation:

- Kerko: [Configuration basics](https://whiskyechobravo.github.io/kerko/latest/config-basics/), [Configuration parameters](https://whiskyechobravo.github.io/kerko/latest/config-params/), [Synchronization](https://whiskyechobravo.github.io/kerko/latest/synchronization/) (the `flask kerko` commands), [How to deploy](https://whiskyechobravo.github.io/kerko/latest/deploying/)
- Docker: [Docker Compose CLI reference](https://docs.docker.com/reference/cli/docker/compose/)
- Cloudflare: [Cloudflare Tunnel](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/), [Cloudflare Access](https://developers.cloudflare.com/cloudflare-one/access-controls/applications/)

## Services


| Service       | Role                                                                                                |
| ------------- | --------------------------------------------------------------------------------------------------- |
| `kerkoapp`    | The KerkoApp web app. Built by `Dockerfile` from `whiskyechobravo/kerkoapp:1.3.0` plus the cover builder's dependencies. |
| `ofelia`      | Scheduler. Runs `flask kerko sync` at :00 and :30, and the incremental cover build at :05 and :35. Pinned to a release. |
| `cloudflared` | Cloudflare Tunnel. Public traffic reaches the stack through it, so no ports are opened on the host. Follows `latest`, as Cloudflare recommends. |
| `portainer`   | Docker management UI. Follows `lts`, as Portainer recommends.                                       |
| `hostshell`   | Idle `alpine` container whose console opens a shell on the server itself. Privileged, so it is only reachable through Portainer behind Cloudflare Access. |


Configuration, templates, the Kerko cache and search index, attachments, and covers are kept under `instance/`. `.env`, `instance/.secrets.toml`, and `instance/kerko/` are gitignored.

## Configuration

Per Kerko's [configuration basics](https://whiskyechobravo.github.io/kerko/latest/config-basics/), public parameters are in `instance/config.toml` (committed) and secrets in `instance/.secrets.toml` (gitignored). The tunnel token goes in `.env` (gitignored). Copy the examples and fill them in:

```bash
cp instance/.secrets.toml.example instance/.secrets.toml
cp .env.example .env
```

`instance/.secrets.toml`:

```toml
SECRET_KEY = "paste-openssl-output-here"
ZOTERO_API_KEY = "your-zotero-api-key"
```

- `SECRET_KEY` ([docs](https://whiskyechobravo.github.io/kerko/latest/config-params/#secret_key)): a long random string, for example the output of `openssl rand -hex 32`.
- `ZOTERO_API_KEY` ([docs](https://whiskyechobravo.github.io/kerko/latest/config-params/#zotero_api_key)): [create a key on zotero.org](https://www.zotero.org/settings/keys/new). Check **Allow library access** and **Allow notes access**; under **Per group permissions** select the OSHF group and choose **Read Only**.

`.env`:

```dotenv
TUNNEL_TOKEN=your-cloudflare-tunnel-token
```

- `TUNNEL_TOKEN`: a [Cloudflare Tunnel](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/) token. See [Tunnel permissions](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/configure-tunnels/remote-tunnel-permissions/).

## How it works

### Startup

Kerko reads `instance/config.toml` and `instance/.secrets.toml` from the `instance/` bind mount. On first start, with no search index yet, `kerkoapp` runs `flask kerko sync`. On later starts it runs `flask kerko clean index` then `flask kerko sync index`, so facet and other schema changes in `config.toml` apply. That rebuild uses the existing cache and does not contact Zotero; new items arrive with Ofelia's next sync. Ofelia's own `flask kerko sync` never cleans the index. Kerko command reference: [Synchronization](https://whiskyechobravo.github.io/kerko/latest/synchronization/).

### Covers

`scripts/build_covers.py` reads items from the search index and writes `instance/static/covers/<item-id>.jpg`. It first looks for a `Cover: https://...` line in the item's Zotero **Extra** field and downloads that image; otherwise it renders the first page of the item's PDF attachment.

### Templates and static files

Custom Jinja templates are in `instance/templates/custom/` and are wired up under `[kerko.templates]` in `instance/config.toml`. Logos and favicons are in `instance/static/`. The container mounts the templates read-only and copies the static files in at startup.

### Storage

`portainer_data` (Portainer's admin user and settings) is the only [named volume](https://docs.docker.com/engine/storage/volumes/); `docker compose down --volumes` deletes it. Everything else is a [bind mount](https://docs.docker.com/engine/storage/bind-mounts/) from the repository directory. Only directories are mounted, never single files, because a missing file bind becomes an empty directory and breaks startup.

### Cloudflare Tunnel and Access

Public traffic reaches the stack through a Cloudflare Tunnel ([create a tunnel](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/get-started/create-remote-tunnel/), [published applications](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/routing-to-tunnel/)). Protect any admin hostname with a [Cloudflare Access application](https://developers.cloudflare.com/cloudflare-one/access-controls/applications/) and an **Allow** [policy](https://developers.cloudflare.com/cloudflare-one/access-controls/policies/) for approved email addresses ([identity providers](https://developers.cloudflare.com/cloudflare-one/identity/idp-integration/)).

Point the public hostname at http://kerkoapp:80, and the Portainer hostname at http://portainer:9000.

### Search engines

Kerko generates an XML sitemap at `https://example.com/bibliography/sitemap.xml` (see [Submitting your sitemap](https://whiskyechobravo.github.io/kerko/latest/deploying/#submitting-your-sitemap-to-search-engines)).

## Running locally

Only `kerkoapp` is needed locally; skip `cloudflared`, `ofelia`, `portainer`, and `hostshell`.

```bash
git clone https://github.com/opensciencehardware/oshf-kerko-library.git
cd oshf-kerko-library
cp instance/.secrets.toml.example instance/.secrets.toml
cp .env.example .env
```

Set `SECRET_KEY` and `ZOTERO_API_KEY` as in [Configuration](#configuration); Kerko requires both even for a public library. Give `TUNNEL_TOKEN` in `.env` any placeholder value; Compose refuses to start while it is blank. If you don't want to use the OSHF library, point `instance/config.toml` at the public [Kerko demo library](https://www.zotero.org/groups/2348869/kerko_demo):

```toml
ZOTERO_LIBRARY_ID = "2348869"
ZOTERO_LIBRARY_TYPE = "group"
```

The Compose file publishes no ports, so publish a host port on `kerkoapp` (for example `8080:80`), then start that service. The site is at `http://localhost:8080/bibliography/` once the first sync finishes. The first `flask kerko sync` fetches the whole Zotero library and can take a while; Zotero throttles API requests, so pauses are normal.
