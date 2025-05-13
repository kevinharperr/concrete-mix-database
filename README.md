# Concrete Mix Database Web Application (Version 1 Prototype)

## Project Overview

This project is a Version 1 prototype of a web application designed to manage and explore data from a PostgreSQL database containing information about concrete materials, mix compositions, performance test results, and sustainability metrics. It provides functionalities for viewing, adding, searching, and filtering concrete mix data, with a focus on usability and data integrity.

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
*   **Core Tables (Managed Externally):**
    *   `bibliographicreference`: Source documents (papers, reports).
    *   `chemicalcomposition`: Chemical makeup of materials.
    *   `concretemix`: Core mix design information.
    *   `datasetversion`: Metadata about data import batches.
    *   `durabilityresult`: Results from durability tests (e.g., chloride permeability).
    *   `material`: Details about raw materials (cement, aggregates, admixtures).
    *   `materialproperty`: Physical properties of materials (density, absorption).
    *   `mixcomposition`: Links materials to a specific `Concretemix` with quantities.
    *   `performanceresult`: Results from performance tests (compressive strength, slump).
    *   `specimen`: Details about the test specimens used.
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
*   `concrete_mix_app/`: The core application for concrete data.
    *   `models.py`: Defines Django models mirroring the database tables.
    *   `views.py`: Contains the logic for handling requests and rendering pages.
    *   `urls.py`: App-specific URL routing.
    *   `forms.py`: Defines forms for data entry and validation.
    *   `filters.py`: Defines filters for the search functionality using `django-filter`.
    *   `admin.py`: Configures how models are displayed in the Django admin site.
    *   `templatetags/`: Contains custom template tags (e.g., `url_params.py`).
*   `templates/`: Project-level HTML templates.
    *   `base.html`: The main site layout template.
    *   `includes/`: Reusable template snippets (e.g., `pagination.html`).
    *   `concrete_mix_app/`: Templates specific to the concrete app (dashboard, detail views, forms, list views).
*   `static/`: Project-level static files (CSS, JavaScript, images) - currently empty, relying on Bootstrap CDN.

## Core Features & Usage (Version 1)

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
    *   Add Composition/Performance/Durability: Use the forms integrated into the Mix Detail page.
*   **Admin Interface (`/admin/`):**
    *   Requires superuser login.
    *   Provides direct access to view, add, edit, and delete data in all registered models (including Django's User/Group models and the concrete data models). Useful for data management and troubleshooting.

## Future Enhancements Roadmap

### Version 2:

*   Advanced data visualization (ternary diagrams, complex charts).
*   Standard compliance checking (ACI, EN, etc.).
*   Sustainability insights dashboards.
*   Data sharing and collaboration features.
*   Project-based access controls.
*   Refined user roles and permissions.
*   Improved UI/UX for forms (e.g., searchable selectors).
*   Bulk data import functionality.

### Version 3:

*   Predictive models for strength prediction.
*   API access for external tools.
*   Advanced machine learning integration.

