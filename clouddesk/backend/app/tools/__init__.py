# app/tools/__init__.py
# Purpose: Marks app/tools as a package. The Phase 2 tool layer (billing/account/technical/
#          product) sits between future agents and the Phase 1 service layer: Agent -> Tool ->
#          Service -> Database (spec section 8). Tools never touch the DB directly.
# Author: CloudDesk Team
# Date: 2026-09-21
