# 📄 Monthly Technical Report

### Author: Mohammad Footuhi

### Scope: Backend, SSO, DevOps, Integration (n8n, Dify, Casdoor, Kong, FastAPI, Logging)

---

## 1. n8n SSO Implementation (Casdoor + Kong)

* **Background:**
  n8n is not multi-tenant by design (even in Enterprise version), unlike Dify. To implement SSO, I first studied **n8n core architecture**, database schema, and authentication workflow.

* **Steps Taken:**

  * Deployed multiple versions of n8n to analyze authentication flow.
  * Reverse-engineered **PostgreSQL schema** (tables: `users`, `projects`, `credentials`, …).
  * Verified that **multi-user support** can be simulated inside a single pod by managing user records directly.
  * Started a **FastAPI-based middleware service** (aligned with our internal coding standards) to orchestrate Casdoor ↔ n8n authentication.

* **Challenges & Solutions:**

  1. **Cookie / Domain Mismatch**

     * Issue: n8n uses cookie-based auth, not sessions. With separate domains for Casdoor, n8n, and panel, cookies failed to propagate.
     * Solution: Standardized domains via **Kong reverse proxy** → unified cookie domain → stable login persistence.

  2. **Passwordless Authentication**

     * Issue: Casdoor does not provide user passwords, while n8n strictly requires them.
     * Solution: Generate a **random password** per Casdoor user → register via n8n API → maintain mapping internally.

  3. **Logout Synchronization**

     * Issue: Casdoor logout did not propagate to n8n; backend service couldn’t directly manipulate n8n cookies.
     * Solution:

       * Implemented **Casdoor Webhook → External FastAPI Service → n8n Logout API**.
       * Used **Kong redirect plugin** to propagate logout events (n8n → Panel → Casdoor).

* **Status:**
  ✅ Working SSO integration with Casdoor for n8n, including login, logout propagation, and multi-user handling.

---

## 2. Dify SSO Integration

* **Background:**
  Dify handles tokens via **localStorage**, not cookies → backend services cannot directly manipulate tokens.

* **Experiments:**

  * Stored **console token + refresh token** in Redis.
  * Injected tokens into cookies (domain-aware, via Kong).
  * Attempted to invalidate tokens manually via API calls.

* **Outcome:**
  None of the backend-controlled approaches worked reliably due to **frontend-localStorage constraints**.

* **Resolution:**
  Escalated issue → collaborated with **Kazem**. Provided laptop access for local implementation. Final logout handling logic implemented on Dify frontend side.

* **Additional Work:**

  * Implemented **reverse logout propagation**: when user logs out from Dify, Kong triggers logout from Panel + Casdoor.

---

## 3. Logging & Observability

* **RFC-Based Logging**

  * Studied **RFC 5424, RFC 5427, RFC 3339** for syslog compliance.
  * Implemented structured logging in services to support future integration with **Elasticsearch + Kibana**.
  * Logging format aligned with **syslog severity levels** and **JSON structured events**.

* **Future-Ready:**
  All user actions in n8n/Dify SSO can now be traced and stored in Elastic with minimal effort.

---

## 4. Kong Enhancements

* Refactored **Kong auth plugin** to handle multiple API key naming conventions.
* Added **redirect plugin logic** for logout synchronization across services.
* Unified **cookie domain policy** across microservices.

---

## 5. Cross-Team Contributions

* Assisted **MLOps team** in designing their SSO integration service.
* Supported **Ehsan** in building the Smart Edea service (troubleshooting + error handling).
* Provided **demo support**, bug fixing, and debugging across multiple services.

---

## 6. Project Deployments & Best Practices

* Applied **corporate coding standards** (styling, logging, configuration via Dynaconf).
* Deployed older services (MCP, etc.) to DML infrastructure.
* Ensured **infrastructure-as-code consistency** across projects.

---

## 7. Other Projects

* **Dr. Rabie Application:**
  Delivered the application that centralizes visibility of all services and projects for each team, improving **team management** and **cross-team coordination**.

* **Corporate-Marketplace Project:**

  * Migrated project to **PostgreSQL backend** with updated docker-compose.
  * Added **database initialization and utility scripts**.
  * Configured **metrics middleware** for observability.
  * Updated **README with full English documentation**.
  * Applied **code quality improvements** (isort, black, style refactors).

* **Kong-Swagger-Generator:**

  * Fixed models and Swagger schemas based on new requirements.
  * Updated **README documentation**.
  * Prepared demo-ready configurations with aligned models.

* **Panel-Links Project:**

  * Added **README documentation** for better onboarding.
  * Refactored **models, serializers, views, and admin** with isort & black formatting.
  * Updated dependencies and synced with latest main branch.

---

## 8. Current Work

* **OCR Integration:**
  Started integrating **dots.ocr** into a FastAPI application for document processing.

* **Refactoring:**
  Writing extended documentation for the n8n service + ongoing refactor to cover more edge cases and ensure maintainability.

---

# ✅ Summary

This month’s work primarily focused on **SSO integration for n8n and Dify**, **observability improvements**, **Kong enhancements**, and **cross-team support**. Major technical challenges (cookie domain mismatch, passwordless authentication, frontend-localStorage constraints) were solved using a combination of **reverse proxy logic, webhook orchestration, and collaborative frontend adjustments**.

Completed: **Dr. Rabie Application** and **multiple project enhancements** (corporate-marketplace, kong-swagger-generator, panel-links).
Ongoing: **OCR integration** and **service refactoring** for long-term stability.