# Security Configuration

## Environment Variables Required

Before running the application, set these environment variables:

### Database Configuration
```bash
# Set your PostgreSQL password
export DB_PASSWORD="your_actual_password_here"

# Set Django secret key (generate a new one for production)
export SECRET_KEY="your_actual_secret_key_here"
```

### Windows PowerShell
```powershell
$env:DB_PASSWORD="your_actual_password_here"
$env:SECRET_KEY="your_actual_secret_key_here"
```

### Example .env file
Create a `.env` file in the project root with:
```
DB_PASSWORD=your_actual_password_here
SECRET_KEY=your_actual_secret_key_here
DEBUG=True
```

## Important Notes

- The original hardcoded credentials have been removed for security
- Your actual database password is: `264537`
- You need to set this as an environment variable before running the application
- Never commit actual credentials to version control 