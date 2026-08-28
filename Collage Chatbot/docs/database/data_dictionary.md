# AIT College AI Assistant — Master Data Dictionary

This document specifies the complete relational schema and field-level metadata for the Ahmedabad Institute of Technology AI Assistant database.

---

## 1. Identity & Access Control

### `users`
| Column Name | Data Type | Constraints | Description |
|---|---|---|---|
| `id` | VARCHAR(36) | PRIMARY KEY | Unique UUID identifier for the user account |
| `email` | VARCHAR(150) | UNIQUE, NOT NULL, INDEX | Primary email login address |
| `hashed_password` | VARCHAR(255) | NOT NULL | PBKDF2/SHA-256 password hash |
| `full_name` | VARCHAR(150) | NOT NULL | User's legal full name |
| `enrollment_number` | VARCHAR(50) | UNIQUE, INDEX, NULLABLE | GTU / AIT unique student enrollment number |
| `is_active` | BOOLEAN | DEFAULT TRUE | Account activation and suspension state |
| `department_id` | VARCHAR(36) | FOREIGN KEY (`departments.id`) | Associated academic department |
| `course_id` | VARCHAR(36) | FOREIGN KEY (`courses.id`) | Enrolled academic program |
| `current_semester` | INTEGER | NULLABLE | Current semester (1 to 8) |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Registration timestamp |
| `updated_at` | TIMESTAMP | AUTO-UPDATE | Last modification timestamp |

### `roles` & `permissions`
| Column Name | Data Type | Constraints | Description |
|---|---|---|---|
| `id` | VARCHAR(36) | PRIMARY KEY | UUID identifier |
| `name` | VARCHAR(50) | UNIQUE, NOT NULL | Role name (`PUBLIC`, `STUDENT`, `FACULTY`, `ADMIN`, `SUPER_ADMIN`) |
| `description` | VARCHAR(255) | NULLABLE | Role scope description |

---

## 2. Academic Master Data

### `fees`
| Column Name | Data Type | Constraints | Description |
|---|---|---|---|
| `id` | VARCHAR(36) | PRIMARY KEY | UUID identifier |
| `course_id` | VARCHAR(36) | FOREIGN KEY (`courses.id`), NOT NULL | Associated course program |
| `academic_year` | VARCHAR(20) | NOT NULL | Academic year (e.g. `2026-27`) |
| `tuition_fee` | FLOAT | NOT NULL | Tuition fee per semester (e.g. `32000.0`) |
| `exam_fee` | FLOAT | DEFAULT 1500.0 | University & internal examination charges |
| `other_charges` | FLOAT | DEFAULT 1000.0 | Library, lab, and activity charges |
| `total_fee` | FLOAT | NOT NULL | Total amount payable |
| `payment_terms` | VARCHAR(255) | NOT NULL | Semester-wise or annual terms |
| `verification_status` | VARCHAR(30) | DEFAULT `VERIFIED` | State: `DRAFT`, `VERIFIED`, `ARCHIVED` |
| `version` | INTEGER | DEFAULT 1 | Version counter for audit trail |
| `ai_visible` | BOOLEAN | DEFAULT TRUE | Governs visibility to the AI Router |

### `faculty` & `faculty_subjects`
| Column Name | Data Type | Constraints | Description |
|---|---|---|---|
| `id` | VARCHAR(36) | PRIMARY KEY | UUID identifier |
| `employee_id` | VARCHAR(50) | UNIQUE, NOT NULL | AIT staff ID (e.g. `AIT-FAC-101`) |
| `name` | VARCHAR(150) | NOT NULL | Faculty full name (e.g. `Prof. Anjali Sharma`) |
| `designation` | VARCHAR(100) | NOT NULL | Title (e.g. `Associate Professor`) |
| `department_id` | VARCHAR(36) | FOREIGN KEY (`departments.id`) | Affiliated department |
| `office_room` | VARCHAR(50) | NULLABLE | Campus room location (e.g. `Block B, Room 204`) |
| `office_hours` | VARCHAR(100) | NULLABLE | Office hours for student consultation |

---

## 3. Visual Media & Provenance

### `facility_images` & `event_images`
| Column Name | Data Type | Constraints | Description |
|---|---|---|---|
| `id` | VARCHAR(36) | PRIMARY KEY | UUID identifier |
| `image_url` | VARCHAR(500) | NOT NULL | Direct URL to verified image asset |
| `source_url` | VARCHAR(500) | NOT NULL | Authoritative page URL on `https://www.aitindia.in` |
| `source_page` | VARCHAR(255) | NOT NULL | Human-readable title of source page |
| `caption` | VARCHAR(255) | NULLABLE | Descriptive caption for visual context |
| `alt_text` | VARCHAR(255) | NULLABLE | Accessible screen-reader text |
| `approval_status`| VARCHAR(30) | DEFAULT `APPROVED` | Approval state: `PENDING`, `APPROVED`, `REJECTED` |
| `ai_visible` | BOOLEAN | DEFAULT TRUE | Allows AI Router to serve in responses |
| `retrieved_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Date retrieved/indexed from official source |

---

## 4. Knowledge & Governance

### `knowledge_conflicts`
| Column Name | Data Type | Constraints | Description |
|---|---|---|---|
| `id` | VARCHAR(36) | PRIMARY KEY | UUID identifier |
| `topic` | VARCHAR(150) | NOT NULL | Conflict subject (e.g. `BCA Fee for 2026-27`) |
| `source_a_type` | VARCHAR(50) | NOT NULL | Source A identifier (e.g. `OFFICIAL_WEBSITE`) |
| `source_a_value`| TEXT | NOT NULL | Value stated by Source A |
| `source_b_type` | VARCHAR(50) | NOT NULL | Source B identifier (e.g. `ADMIN_DATABASE`) |
| `source_b_value`| TEXT | NOT NULL | Value recorded in Source B |
| `status` | VARCHAR(30) | DEFAULT `OPEN` | State: `OPEN`, `RESOLVED`, `DISMISSED` |
| `resolution_choice` | VARCHAR(50) | NULLABLE | Choice: `KEEP_WEBSITE`, `KEEP_DATABASE`, `CUSTOM` |
