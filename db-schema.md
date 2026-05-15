# mu2edaq-runlog-db — Schema Diagram

Derived from `db-schema.txt`. Foreign-key relationships are inferred from
column names and types (the source dump does not include constraint metadata),
so a few edges may need confirmation against the live database.

## Active core schema

```mermaid
erDiagram
    run ||--o{ subrun           : "has"
    run ||--o| run_end_info     : "ended by"
    run ||--o{ run_transition   : "transitions"
    run ||--o{ config           : "per-subsystem config"
    run ||--o{ artdaq_fcl       : "FCL documents"
    run }o--|| run_type         : "run_type_id"

    run_transition }o--|| run_transition_type  : "type_id"
    run_transition }o--o| run_transition_cause : "cause_id"

    run {
        bigint   run_number PK
        varchar  comment
        timestamptz create_time
        varchar  run_type
        int      run_type_id FK
    }

    subrun {
        int    run PK,FK
        int    subrun PK
        bigint n_events
        bigint n_on_spill
        bigint n_off_spill
        bigint n_null
        bigint min_ewt
        bigint max_ewt
        int    start_time_unix
        int    stop_time_unix
        jsonb  event_mode_counts
        timestamptz created_at
    }

    run_end_info {
        int   run_number PK,FK
        text  comment
        timestamp create_time
    }

    run_transition {
        bigint run_number FK
        int    type_id FK
        int    cause_id FK
        timestamptz transition_time
    }

    run_transition_type {
        int     id PK
        varchar name
        varchar description
    }

    run_transition_cause {
        int     id PK
        varchar name
    }

    run_type {
        int     id PK
        varchar name
        varchar description
    }

    config {
        int   run_number PK,FK
        text  subsystem  PK
        jsonb config
        timestamptz create_time
    }

    artdaq_fcl {
        int     run_number PK,FK
        varchar name       PK
        varchar label
        text    content
    }
```

## Derived views

Read-only views built on top of the core tables. They expose pre-joined
projections for UI/reporting and have no FK relationships of their own.

```mermaid
flowchart LR
    run[(run)] --> vrs[view_run_summary]
    run --> vrc[view_run_config]
    run --> vrss[view_run_subsystems]
    run --> vrdbs[view_run_db_services]
    run --> vct[view_config_trigger]

    config[(config)] --> vrc
    config --> vrss
    config --> vrdbs
    config --> vct

    run_end_info[(run_end_info)] --> vrs
    run_type[(run_type)] --> vrs
    run_type --> vrc
    run_type --> vrss
```

## Legacy / unused tables

These tables are marked `_notused` or `_old` in the dump and are not part of
the proposed organization. Kept here for reference during the migration.

| Table | Notes |
|---|---|
| `artdaq_components_notused` | Per-rank artdaq process inventory (host/port/label/subsystem). |
| `config_old` | Previous monolithic config table; superseded by `config`. |
| `config_subsystem_notused` | Old per-subsystem config alias / version metadata. |
| `config_subsystem_data_notused` | Old per-subsystem JSON payload split out of `config_subsystem_notused`. |
| `detector_setup_notused` | Lookup table referenced by `config_old.detector_setup_id`. |
| `run_summary_notused` | Earlier per-run summary blob; replaced by `view_run_summary`. |
