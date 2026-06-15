# EPK Migration Runbook & Rollback Plan

> **Source platform:** Base44 (proprietary, locked-in)  
> **Target platform:** Self-hosted on Hetzner Cloud (PostgreSQL, Redis, MinIO, kubeadm K8s + Hetzner LB + DNS)  
> **Estimated timeline:** 10–11 weeks (per architecture audit)  
> **Critical blockers:** 7 requiring full reimplementation, 3 partial, 5 platform constraints

---

## Phase 0 — Pre-Migration Setup

### Prerequisites
- [ ] Hetzner Cloud account with API token configured
- [ ] Domain DNS managed in Hetzner (or delegated NS records)
- [ ] Terraform ≥ 1.6 installed and validated (`terraform validate` passes)
- [ ] kubectl, helm, psql, redis-cli available locally
- [ ] Base44 admin access for data export
- [ ] Staging environment deployed and smoke-tested
- [ ] Runbook reviewed and signed off by team

### Environment Variables (secrets)
| Variable | Source | Target |
|---|---|---|
| `HETZNER_TOKEN` | 1Password / Vault | TF_VAR_hcloud_token |
| `DOMAIN` | DNS zone | `epk.example.com` |
| `DB_PASSWORD` | Generated | PostgreSQL superuser |
| `REDIS_PASSWORD` | Generated | Redis ACL |
| `MINIO_ACCESS_KEY` / `MINIO_SECRET_KEY` | Generated | MinIO root |
| `JWT_SECRET` | Generated (256-bit) | Auth service |
| `OAUTH_*_CLIENT_ID` / `OAUTH_*_SECRET` | Provider dashboards | 6 OAuth connectors |

---

## Phase 1 — Data Export from Base44

### 1.1 Export Strategy
- **Frontend-only export:** Base44 GitHub export contains only React frontend code. Backend (DB, auth, functions, realtime) is proprietary and **not exported**.
- **Data export:** Use Base44 admin dashboard → "Export Data" (JSON/CSV per entity). For large datasets, request Base44 support for full DB dump.
- **Entities to export:** All inferred EPK entities from audit (users, projects, tasks, comments, attachments, subscriptions, webhooks, audit_logs, etc.).

### 1.2 Export Checklist
- [ ] Inventory all entities from `base44-audit.md` data models section
- [ ] Request full DB dump from Base44 support (if dataset > 100k rows)
- [ ] Export each entity to dated directory: `exports/YYYYMMDD/<entity>.json`
- [ ] Verify row counts match admin dashboard counters
- [ ] Compute SHA256 checksums for each file; store in `exports/YYYYMMDD/CHECKSUMS.txt`
- [ ] Archive to cold storage (S3/MinIO) with retention tag

### 1.3 Known Limitations
- No access to Base44 internal IDs for auth users (map by email)
- Realtime subscription state not exportable — rebuild from scratch
- File attachments stored in Base44 CDN — download URLs expire in 24h

---

## Phase 2 — Schema Transformation Scripts

### 2.1 Mapping Rules (MongoDB-compat → PostgreSQL + RLS)
| Base44 Type | Postgres Type | Notes |
|---|---|---|
| `ObjectId` | `uuid` (gen_random_uuid()) | PK on all tables |
| `Date` | `timestamptz` | UTC normalized |
| `DBRef` | `uuid` FK + RLS policy | Enforce ownership |
| `Array<subdoc>` | JSONB column / child table | Normalize if queried |
| `Binary` | `bytea` or MinIO object ref | > 1MB → MinIO |

### 2.2 Transformation Pipeline
```
exports/YYYYMMDD/*.json
      │
      ▼
scripts/transform/
  ├── 01_normalize_ids.py      # ObjectId → UUID, build ID map
  ├── 02_flatten_arrays.py     # Subdoc arrays → child tables
  ├── 03_enforce_rls.py        # Add owner_id, gen policies
  ├── 04_attachments_to_minio.py  # Download + upload, rewrite refs
  └── 05_validate_schema.py    # pg_dump --schema-only diff
      │
      ▼
staging_import/YYYYMMDD/*.sql
```

### 2.3 Script Checklist
- [ ] `01_normalize_ids.py` — deterministic UUID v5 (namespace = Base44 export ID)
- [ ] `02_flatten_arrays.py` — configurable depth (default 1), foreign keys indexed
- [ ] `03_enforce_rls.py` — generates `CREATE POLICY` per table per role (anon, user, admin)
- [ ] `04_attachments_to_minio.py` — parallel downloads (8 workers), resumable, Verifies checksums
- [ ] `05_validate_schema.py` — compares generated DDL against `schema/target.sql` (committed)
- [ ] All scripts: idempotent, structured JSON logs, exit code 0 on success
- [ ] Unit tests for each transform (`tests/transform/test_*.py`)

---

## Phase 3 — Import Validation

### 3.1 Staging Import Procedure
```bash
# 1. Fresh staging DB (Terraform destroys/recreates)
terraform -chdir=infra/terraform apply -target=hcloud_server.db -auto-approve

# 2. Run schema
psql "$STAGING_DB_URL" -f schema/target.sql

# 3. Load data
psql "$STAGING_DB_URL" -f staging_import/YYYYMMDD/01_core.sql
psql "$STAGING_DB_URL" -f staging_import/YYYYMMDD/02_relations.sql
psql "$STAGING_DB_URL" -f staging_import/YYYYMMDD/03_attachments.sql

# 4. Validate
python scripts/validate_import.py --env staging
```

### 3.2 Validation Checks
| Check | Tool | Threshold |
|---|---|---|
| Row count per table | `validate_import.py` | ±0.1% vs export |
| Referential integrity | `pg_dump --data-only --inserts` | 0 FK violations |
| RLS policy coverage | `SELECT * FROM pg_policies` | 100% tables with owner_id |
| Attachment checksums | MinIO `mc stat` + DB `file_sha256` | 100% match |
| Auth user mapping | `validate_import.py --auth` | 100% emails mapped |
| Index usage | `pg_stat_user_indexes` | No unused indexes > 100MB |

### 3.3 Import Checklist
- [ ] Staging DB provisioned fresh (no residual data)
- [ ] Schema applied without errors
- [ ] All 3 data batches loaded in order
- [ ] Validation script exits 0
- [ ] Spot-check 10 random entities end-to-end (UI + API)
- [ ] Performance baseline: `EXPLAIN ANALYZE` on top 5 queries < 50ms p95

---

## Phase 4 — DNS Cutover

### 4.1 Pre-Cutover (T-24h)
- [ ] TTL on all `epk.example.com` records reduced to 60s
- [ ] Hetzner Load Balancer health checks passing (green for 1h)
- [ ] Staging promoted to "candidate" — same infra, separate DNS label `candidate.epk.example.com`
- [ ] Team smoke test on candidate (Phase 5) passes
- [ ] Rollback DNS records pre-staged in Hetzner DNS console

### 4.2 Cutover Procedure (T=0)
```bash
# 1. Verify candidate one last time
curl -sf https://candidate.epk.example.com/healthz

# 2. Switch apex + www CNAME in single API call (atomic)
hcloud dns record update --zone epk.example.com --id <apex_id> --value <lb_ip>
hcloud dns record update --zone epk.example.com --id <www_id>  --value <lb_ip>

# 3. Confirm propagation (check from 3 regions)
for r in us eu asia; do dig @$r.epk.example.com +short; done

# 4. Update TTL back to 3600
hcloud dns record update --zone epk.example.com --id <apex_id> --ttl 3600
```

### 4.3 Post-Cutover (T+0 to T+1h)
- [ ] Monitor LB request rate, error rate, latency (Grafana dashboard)
- [ ] Verify realtime WebSocket connections establishing
- [ ] Confirm OAuth redirects resolve to new domain
- [ ] Run automated smoke suite (Phase 5) every 5 min for 30 min

---

## Phase 5 — Smoke Tests

### 5.1 Automated Suite (`scripts/smoke_test.py`)
| Test | Description | Timeout |
|---|---|---|
| `healthz` | GET `/healthz` returns 200 + `{"status":"ok"}` | 5s |
| `auth_login` | POST `/auth/login` → JWT + refresh cookie | 10s |
| `auth_refresh` | POST `/auth/refresh` rotates tokens | 5s |
| `oauth_google` | Full OAuth flow (headless) | 30s |
| `crud_project` | Create → Read → Update → Delete project | 15s |
| `realtime_sub` | WS connect → subscribe → receive event | 20s |
| `file_upload` | POST `/files` → 201 + MinIO object exists | 30s |
| `webhook_delivery` | Trigger webhook → verify signature + retry | 30s |

### 5.2 Manual Spot-Checks
- [ ] Login as admin, create project, invite team member
- [ ] Team member accepts invite, sees project
- [ ] Realtime: open two browsers, edit same task → sync < 500ms
- [ ] File upload > 10MB → progress bar, thumbnail generates
- [ ] Export project data (CSV) → downloads correctly

### 5.3 Smoke Test Checklist
- [ ] Automated suite: 8/8 pass
- [ ] Manual spot-checks: 5/5 pass
- [ ] No console errors in browser devtools
- [ ] All OAuth providers redirect to correct callback URL
- [ ] Webhook endpoints receive and verify signatures

---

## Phase 6 — Rollback Triggers & Procedure

### 6.1 Automatic Rollback Triggers
| Metric | Threshold | Window | Action |
|---|---|---|---|
| HTTP 5xx rate | > 5% | 5 min | Auto-rollback DNS |
| p95 latency | > 2s | 5 min | Alert + manual decision |
| WebSocket connect failure | > 10% | 5 min | Alert + manual decision |
| DB replication lag | > 30s | 2 min | Alert + manual decision |
| Smoke test failure | Any critical test fails | 1 run | Auto-rollback DNS |

### 6.2 Manual Rollback Decision Matrix
| Scenario | Decision | Owner |
|---|---|---|
| Single non-critical test flaky | Investigate, re-run | On-call |
| Multiple critical tests fail | **Rollback immediately** | On-call |
| Data inconsistency reported | **Rollback immediately** | TL + On-call |
| Performance degrade, recovering | Monitor 15 min, then decide | TL |

### 6.3 Rollback Procedure (DNS-based, < 2 min)
```bash
# 1. Revert DNS to Base44 (pre-staged records)
hcloud dns record update --zone epk.example.com --id <apex_id> --value <base44_ip>
hcloud dns record update --zone epk.example.com --id <www_id>  --value <base44_ip>

# 2. Verify Base44 responding
curl -sf https://epk.example.com/healthz

# 3. Notify team + stakeholders
./scripts/notify.py --channel "#epk-migration" --text "ROLLBACK executed at $(date -u +%H:%M UTC). Base44 live."

# 4. Preserve staging for forensics
#    (Terraform does NOT destroy — keep candidate env)
```

### 6.4 Post-Rollback
- [ ] Document incident in `incidents/YYYYMMDD-rollback.md`
- [ ] Root cause analysis within 48h
- [ ] Fix → re-run Phase 3 validation → schedule new cutover

---

## Phase 7 — Post-Migration (T+24h to T+7d)

### 7.1 Stabilization Checklist
- [ ] Monitoring dashboards green for 24h
- [ ] No P1/P2 incidents
- [ ] Backup/restore drill: restore staging from prod snapshot
- [ ] Cost review: Hetzner bill vs projection
- [ ] Documentation updated: `DEPLOYMENT.md`, `ARCHITECTURE.md`
- [ ] Team retrospective scheduled

### 7.2 Decommission Base44 (T+7d)
- [ ] Confirm zero traffic to Base44 (Cloudflare analytics)
- [ ] Cancel Base44 subscription
- [ ] Revoke Base44 API keys / OAuth credentials
- [ ] Archive final Base44 export to cold storage (7-year retention)

---

## Appendix A — Command Reference

```bash
# Deploy staging
terraform -chdir=infra/terraform apply -var environment=staging

# Deploy prod (after cutover approval)
terraform -chdir=infra/terraform apply -var environment=prod

# Run smoke tests
python scripts/smoke_test.py --env prod --junit output/smoke.xml

# Validate import
python scripts/validate_import.py --env staging --strict

# Generate checksums
sha256sum exports/YYYYMMDD/*.json > exports/YYYYMMDD/CHECKSUMS.txt

# Notify team
python scripts/notify.py --channel "#epk-migration" --text "Message"
```

---

## Appendix B — Contacts

| Role | Name | Primary | Escalation |
|---|---|---|---|
| Migration Lead | | | |
| Backend TL | | | |
| DevOps | | | |
| Base44 Support | support@base44.com | Ticket | Phone: +1-xxx-xxx-xxxx |
| Hetzner Support | support@hetzner.com | Ticket | |

---

## Sign-Off

| Phase | Reviewer | Date | Signature |
|---|---|---|---|
| Pre-Migration | | | |
| Data Export | | | |
| Schema Transform | | | |
| Import Validation | | | |
| DNS Cutover | | | |
| Smoke Tests | | | |
| Post-Migration | | | |

---

*Generated from Base44 audit (t_014f13b3) and Terraform infra (t_a8af80b0). Review with team before execution.*