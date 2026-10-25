# pl_ingest_history - land the five history CSVs from GitHub into `lh_brightcart/Files/bronze/history/` (Lab 1)

**Pattern:** two parameters → ForEach over the file names (parallel) → Copy data, HTTP (anonymous) → Lakehouse Files, binary copy.
A binary copy moves the bytes as they are: no schema, no parsing. `nb_01_bronze_to_silver` does the typing.

## 1. Create the pipeline

Workspace `ws-brightcart-dp` → **+ New item** → **Pipeline** → name `pl_ingest_history`. Start from a blank canvas (not the Copy assistant).

## 2. Parameters (click the canvas background → **Parameters** tab → **+ New**)

| Name | Type | Default value |
|---|---|---|
| `baseUrl` | String | `https://raw.githubusercontent.com/lostspace003/fabric-course/main/data/history` |
| `files` | Array | `["customers.csv","orders.csv","shipments.csv","daily_ops.csv","weather_daily.csv"]` |

The array is `history_files` from `data/manifest.json`; `baseUrl` is the manifest's `baseUrl` + `/history`.

## 3. HTTP connection (once)

**Settings ⚙ → Manage connections and gateways → + New** (or create it inline from the Copy activity's connection dropdown):

| Field | Value |
|---|---|
| Connection type | **HTTP** (listed as *Web* in the connection dialog ⟲ verify) |
| URL | `https://raw.githubusercontent.com` (base only; the activity supplies the relative URL) |
| Authentication | **Anonymous** ⟲ verify at recording: the HTTP connection page lists Anonymous for Copy, while the connector overview table lists only Basic. If Anonymous is missing, use Basic with any dummy user/password: raw.githubusercontent.com ignores credentials. |
| Privacy level | Public (or Organizational) |

## 4. ForEach activity

Activities → **ForEach** → drag to canvas.

| Tab | Setting | Value |
|---|---|---|
| General | Name | `ForEachFile` |
| Settings | Sequential | **off** (parallel) |
| Settings | Batch count | `5` |
| Settings | Items | `@pipeline().parameters.files` (Add dynamic content) |

## 5. Copy data inside the ForEach (select the ✎ pencil on the ForEach → **+** → Copy data)

**Source tab**

| Setting | Value |
|---|---|
| Connection | the HTTP connection from step 3 |
| Connection type | HTTP |
| Relative URL | `@{replace(pipeline().parameters.baseUrl, 'https://raw.githubusercontent.com', '')}/@{item()}` → resolves to `/lostspace003/fabric-course/main/data/history/orders.csv` |
| File format | **Binary** ⟲ verify the label ("File settings" → Binary) |
| Request method | GET |

Simpler alternative if the dialog allows a full URL in the connection: put `@pipeline().parameters.baseUrl` in the connection URL and only `@{item()}` in Relative URL. The expression above keeps a single reusable connection.

**Destination tab**

| Setting | Value |
|---|---|
| Connection | `lh_brightcart` (Workspace → Lakehouse) |
| Root folder | **Files** |
| File path | directory `bronze/history`, file name `@{item()}` |
| File format | **Binary** (source and destination must both be binary for a binary copy) |

**Settings tab:** leave defaults (no staging). General → Name `CopyFile`.

## 6. Save, run, watch

1. **Home → Save**, then **Run**. Five parallel Copy runs appear in the **Output** pane; each should read/write one file.
2. Open **Monitoring hub** (left nav) → the pipeline run → activity details show bytes copied. ⟲ verify the nav label.
3. Open `lh_brightcart` → **Files → bronze → history**: five files.
4. ✅ Run the check cell at the end of `nb_00_bootstrap` (or `nb_01`'s first cells): row counts match `data/manifest.json`
   (customers 8,000 · orders 90,450 · shipments 90,000 · daily_ops 2,568 · weather_daily 7,692).

## 7. If this fails

| Symptom | Cause / fix |
|---|---|
| HTTP 404 | wrong `baseUrl` (branch is `main`, folder is `data/history`) or a file name typo in `files` |
| 401/403 on HTTP | connection auth: use Anonymous (or dummy Basic) |
| "Item creation blocked" | workspace is not on the trial / a capacity |
| Files land but with 0 bytes | source format was not Binary; set Binary on both sides |
| Shortcut tables missing for Lab 2 | Part 2 skipped → run `nb_00_bootstrap` (it also lands these files) |

## 8. Schedule

None. This is a one-time load; the nightly work is `pl_nightly_delivery_promise`.
