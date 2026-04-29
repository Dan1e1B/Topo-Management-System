# TopoPB - Gestão de Trabalhos

This is a web-based management system for topographic surveying works (or similar job management). It allows users to manage client information, work details, invoices, and generate reports.

## Features

- User authentication (login/logout)
- Add, edit, delete, and view works/jobs
- Client management with details like name, NIF, address, contact
- Work tracking with dates (receipt, start, close, delivery, invoicing)
- Invoice management with numbers and values
- Budget and invoicing values
- Work descriptions and file names
- Location and coordinates
- Task lists
- Automatic database backups (up to 50 backups)
- Reports by client and invoicing period

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/Dan1e1B/Topo-Management-System.git
   cd "Topo-Management-System"
   ```

2. Install Python dependencies:
   ```
   pip install flask
   ```

3. Set environment variables (optional, but recommended for security):
   - `SECRET_KEY`: Secret key for Flask sessions (generate a random string)
   - `ADMIN_USER`: Admin username (default: admin)
   - `ADMIN_PASSWORD`: Admin password (default: defaultpassword)
   - `DATABASE_PATH`: Path to SQLite database file (default: trabalhos.db)
   - `BACKUP_DIR`: Directory for backups (default: backup)

   Example:
   ```
   export SECRET_KEY="your-random-secret-key"
   export ADMIN_USER="yourusername"
   export ADMIN_PASSWORD="yourpassword"
   ```

4. Run the application:
   ```
   python app.py
   ```

5. Open your browser and go to `http://localhost:5000`

## Usage

- Login with the admin credentials.
- Navigate through the interface to add/edit works, view reports, etc.
- The app uses SQLite for data storage, so no additional database setup is required.

