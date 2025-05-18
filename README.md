# Concrete Mix Database Web Application

## Project Overview

This web application is designed to manage and explore data from a PostgreSQL database containing information about concrete materials, mix compositions, performance test results, and sustainability metrics. It provides functionalities for viewing, adding, searching, and filtering concrete mix data, with a focus on usability and data integrity. The application has been consolidated into a single "cdb_app" structure for improved maintainability.

## Technology Stack

*   **Backend Framework:** Python 3.x with Django 5.x
*   **Database:** PostgreSQL (connected via `psycopg2-binary`)
*   **Frontend:** Django Templates, Bootstrap 5
*   **Forms:** Django Forms with `django-crispy-forms` and `crispy-bootstrap5`
*   **Authentication:** `django-allauth` (handling email/password and Google Sign-In setup)
*   **Filtering:** `django-filter`

## Installation & Setup (Local Development - Windows)

Follow these steps to set up the project locally:

1.  **Prerequisites:**
    *   Python 3.x installed (ensure it's added to your PATH).
    *   PostgreSQL installed and running.
    *   pgAdmin 4 or another PostgreSQL client installed.
    *   Git installed (optional, but recommended for version control).

2.  **Database Setup:**
    *   Using pgAdmin 4 or `psql`, create a new PostgreSQL database named `concrete_mix_db`.
    *   Ensure you have a user (e.g., the default `postgres` user) with a password that can access this database. The default credentials used in `settings.py` are:
        *   User: `postgres`
        *   Password: `264537`
        *   Host: `localhost`
        *   Port: `5432`
    *   Make sure the required tables (`bibliographicreference`, `concretemix`, `material`, etc.) already exist in the `concrete_mix_db` database with the correct schema, as this project uses `managed = False` for these models.

3.  **Clone the Repository (if applicable):**
    ```bash
    git clone <repository_url>
    cd concrete_mix_project
    ```
    If you don't have a repository, create a project folder manually (`mkdir concrete_mix_project` and `cd concrete_mix_project`).

4.  **Create and Activate Virtual Environment:**
    ```bash
    # Create the environment
    python -m venv venv

    # Activate the environment (Windows CMD/PowerShell)
    venv\Scripts\activate
    ```

5.  **Install Required Packages:**
    ```bash
    pip install django psycopg2-binary django-crispy-forms crispy-bootstrap5 django-allauth djangorestframework django-filter
    ```
    *(Note: `djangorestframework` is installed but not actively used in V1 UI yet).*

6.  **Configure Settings:**
    *   Open `concrete_mix_project/settings.py`.
    *   Verify the `DATABASES['default']` section matches your PostgreSQL connection details (NAME, USER, PASSWORD, HOST, PORT). **Important:** For production, never hardcode passwords; use environment variables or a secrets management system.

7.  **Apply Django Migrations:**
    *   This command creates the database tables required by Django's built-in apps (auth, admin, sessions, etc.) and third-party apps like `allauth`. It will *not* affect your existing concrete data tables because `managed = False` is set in their models.
    ```bash
    python manage.py migrate
    ```

8.  **Create a Superuser (for Admin Access):**
    ```bash
    python manage.py createsuperuser
    ```
    Follow the prompts to create an administrator account.

9.  **Run the Development Server:**
    ```bash
    python manage.py runserver
    ```

10. **Access the Application:**
    *   Open your web browser and go to `http://127.0.0.1:8000/`.
    *   You should be redirected to the login page (`/accounts/login/`).
    *   You can sign up for a new user account or log in.

## Database

*   **System:** PostgreSQL
*   **Database Name:** `concrete_mix_db`
*   **Core Tables:**
    *   `bibliographic_reference`: Source documents (papers, reports).
    *   `material`: Core material information.
    *   `material_property`: Properties of materials.
    *   `material_class`: High-level material classifications (e.g., "cement", "SCM").
    *   `concrete_mix`: Core mix design information.
    *   `mix_component`: Links materials to concrete mixes with dosage information.
    *   `performance_result`: Results from performance tests (e.g., compressive strength).
    *   `sustainability_metric`: Environmental impact values (e.g., CO2 emissions, energy use).
    *   `dataset`: Information about source datasets.
    *   `specimen`: Test specimen details.
    *   `test_method`: Test methods used for performance results.
    *   `unit_lookup`: Units and conversion factors.
    *   `sustainabilitymetrics`: Environmental impact data for mixes.
*   **Django Model Management:** The Django models corresponding to the tables above have `class Meta: managed = False`. This means Django will *not* create, modify, or delete these tables during migrations. They are assumed to exist and be managed externally (e.g., via pgAdmin or separate scripts). Django *will* manage tables for its own apps (auth, admin, sessions) and third-party apps (`allauth`).
*   **Primary Key Sequences:** If you encounter `IntegrityError` related to duplicate primary keys (e.g., `material_id`, `mix_id`) when adding data through the web application after manual database operations, the PostgreSQL sequence generators might be out of sync. You can reset them using `setval` in pgAdmin:
    ```sql
    -- Example for material table (replace sequence/table/column names if different)
    SELECT setval('material_material_id_seq', (SELECT MAX(material_id) FROM material));
    -- Example for concretemix table
    SELECT setval('concretemix_mix_id_seq', (SELECT MAX(mix_id) FROM concretemix));
    ```

## Application Structure

*   `manage.py`: Django's command-line utility.
*   `concrete_mix_project/`: Main project directory.
    *   `settings.py`: Project configuration (database, apps, static files, etc.).
    *   `urls.py`: Project-level URL routing.
    *   `wsgi.py`/`asgi.py`: Server gateway interfaces.
*   `cdb_app/`: The core application for concrete mix database.
    *   `models.py`: Defines Django models reflecting the refined database schema.
    *   `views.py`: Contains the logic for handling requests and rendering pages.
    *   `urls.py`: App-specific URL routing.
    *   `forms.py`: Defines forms for data entry and validation.
    *   `filters.py`: Defines filters for the search functionality using `django-filter`.
    *   `admin.py`: Configures how models are displayed in the Django admin site.
    *   `templatetags/`: Contains custom template tags (e.g., `url_params.py`).
    *   `api_views.py`: REST API endpoints for the application.
*   `templates/`: Project-level HTML templates.
    *   `cdb_base.html`: The main site layout template.
    *   `includes/`: Reusable template snippets (e.g., `pagination.html`).
    *   `cdb_app/`: Templates specific to the concrete database app (dashboard, detail views, forms, list views).
*   `static/`: Project-level static files (CSS, JavaScript, images) - currently empty, relying on Bootstrap CDN.

## Performance Testing Framework

The project includes a robust performance testing framework designed to evaluate database import performance and identify potential bottlenecks:

* **Components:**
  * `performance_testing.py`: Main script for generating test datasets and measuring import performance
  * `PerformanceMetrics` class: Tracks CPU/memory usage, query counts, and execution times
  * `TestDataGenerator` class: Creates synthetic datasets of configurable sizes
  * `TestRunner` class: Orchestrates test execution and collects results

* **Features:**
  * **CSV-based Testing**: Uses CSV as the primary format for compatibility with existing ETL pipelines
  * **Scalable Testing**: Supports creating datasets of varying sizes to analyze scaling behavior
  * **Performance Analysis**: Calculates linear/superlinear/sublinear scaling factors
  * **Resource Monitoring**: Tracks memory usage, query counts, and database operations
  * **Production Estimates**: Generates estimates for production dataset import times

* **Usage:**
  ```bash
  python performance_testing.py --sizes 1 2 5 10 --iterations 3 --output performance_report.json
  ```
  * `--sizes`: Multiplier sizes for test datasets (e.g., 1x, 2x, 5x, 10x base size)
  * `--iterations`: Number of test runs per size for statistical validity
  * `--output`: Path to save JSON performance report

## Core Features & Usage

*   **Authentication:**
    *   Sign up: `/accounts/signup/`
    *   Login: `/accounts/login/`
    *   Logout: `/accounts/logout/`
    *   Password Management: `/accounts/password/...`
    *   (Google Sign-In is configured in `settings.py` but requires client ID/secret setup).
*   **Dashboard (`/`):**
    *   Displays basic statistics (total mixes, materials, test results).
    *   Shows a list of the 5 most recently added concrete mixes, linked to their detail pages.
    *   Includes an accordion showing the basic composition of recent mixes.
*   **Search Mixes (`/mixes/`):**
    *   Filter mixes by: Mix Code/ID, Region, Source Dataset, Material Type contained in the mix, Compressive Strength range, and Test Age.
    *   Results are paginated (25 per page).
    *   Table headers for Mix Code, Region, and Date Created are clickable for sorting.
    *   Results table shows basic mix info and the first available compressive strength result.
*   **Mix Detail (`/mixes/<mix_id>/`):**
    *   Displays general information about the selected mix.
    *   Shows tables for related Mix Composition, Performance Results, Durability Results, and Sustainability Metrics.
    *   Includes forms directly on the page to add new Composition items, Performance results, and Durability results associated with the current mix.
    *   Materials listed in the composition table link to their respective detail pages.
*   **Material Detail (`/materials/<material_id>/`):**
    *   Displays general information about the selected material.
    *   Shows related Material Properties and Chemical Compositions.
    *   Lists all Concrete Mixes that use this material, linking back to their detail pages.
*   **Adding Data:**
    *   Add New Material: `/materials/add/` (redirects to detail page on success).
    *   Add New Concrete Mix: `/mixes/add/` (redirects to detail page on success).
    *   Add Components/Performance Results: Use the forms integrated into the Mix Detail page.
    *   Add Datasets: `/datasets/add/` for adding new datasets.
*   **Admin Interface (`/admin/`):**
    *   Requires superuser login.
    *   Provides direct access to view, add, edit, and delete data in all registered models (including Django's User/Group models and the concrete data models). Useful for data management and troubleshooting.

## Recent Updates

### Version 1.0.1 (May 13, 2025)
*   Fixed field name inconsistencies after transition to single-app structure.
*   Fixed relationship name references to ensure database consistency.
*   Fixed JavaScript chart rendering in mix detail pages.

### Version 1.0.0 (May 13, 2025)
*   Consolidated application architecture - retired concrete_mix_app and transitioned to a single application (cdb_app).
*   Updated all templates to extend `cdb_base.html` instead of `base.html`.
*   Updated branding throughout to "Concrete Mix Database" instead of "CDB - Concrete Database".

## PhD Research Priorities and Development Roadmap

### Near-Term TODOs (Focus on Analysis with Existing Data):

1. **Strength Classification System (EN & ASTM Standards)**
   * Add concrete strength class fields (C20/25, C25/30, etc. for EN; 3000psi, 4000psi, etc. for ASTM)
   * Implement automatic classification based on 28-day strength results
   * Create filtered views by strength class

2. **Data Completeness Assessment**
   * Add completeness indicators for each mix record (basic/complete)
   * Implement data validation rules for critical parameters
   * Flag mixes with missing essential components (cement, water)

3. **Basic Parameter Correlation Analysis**
   * Create scatter plot visualizations for key relationships:
     - Water-cement ratio vs. strength
     - Cement content vs. strength
     - Supplementary material proportions vs. strength
   * Add statistical correlation indicators (R²)

4. **Clinker Reduction Analysis**
   * Add clinker factor calculation field
   * Create visualization comparing clinker factor to strength development
   * Implement clinker replacement ratio metrics

5. **Mix Composition Comparison Tool**
   * Implement side-by-side comparison view for multiple mixes
   * Add normalized comparison metrics (per m³, per MPa)
   * Create visual highlighting of key differences between compositions

6. **Performance Data Export**
   * Add CSV/Excel export with complete mix data
   * Create customizable export templates for research analysis
   * Implement batch export for statistical processing

### Medium-Term Features (Version 2):

*   Advanced data visualization (ternary diagrams, complex charts)
*   Standard compliance checking (ACI, EN, etc.)
*   Sustainability insights dashboard (when metrics become available)
*   Data sharing and collaboration features
*   Improved UI/UX for forms (e.g., searchable selectors)
*   Bulk data import functionality

### Long-Term Features (Version 3):

*   Predictive models for strength, workability, and durability
*   Performance optimization tools for low-carbon mix design
*   Advanced machine learning integration
*   Comprehensive sustainability assessment

