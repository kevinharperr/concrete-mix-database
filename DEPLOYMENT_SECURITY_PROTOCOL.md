# Deployment Security Protocol

**Created**: 02.06.2025, 17:30  
**Purpose**: Prevent critical security deployment incidents  
**Trigger**: 5-hour production outage due to environment variable deployment failure  

## 🚨 **MANDATORY DEPLOYMENT RULES**

This protocol is **MANDATORY** for all deployments involving:
- Environment variable changes
- Security configuration modifications  
- Credential management updates
- Authentication/authorization changes

**VIOLATION OF THIS PROTOCOL IS PROHIBITED** - Following this incident, adherence is required to prevent similar outages.

## **Pre-Deployment Checklist**

### **Phase 1: Environment Preparation** ✅

**Before writing any code that requires environment variables:**

- [ ] **Document Requirements**: List all new environment variables required
- [ ] **Plan Fallbacks**: Define appropriate fallback values for development
- [ ] **Create Setup Instructions**: Write clear, step-by-step environment setup guide
- [ ] **Test Instructions**: Verify setup instructions work with fresh environment
- [ ] **Team Notification**: Send 24-hour advance notice of environment requirements

### **Phase 2: Development Validation** ✅

**Before committing environment variable changes:**

- [ ] **Local Testing**: Verify application starts with environment variables configured
- [ ] **Fallback Testing**: Verify application starts without environment variables (fallbacks work)
- [ ] **Fresh Environment Test**: Test setup instructions on clean system/environment
- [ ] **Documentation Review**: Ensure setup instructions are clear and complete
- [ ] **Edge Case Testing**: Test with missing variables, invalid values, empty values

### **Phase 3: Staging Validation** ✅

**Before deploying to production:**

- [ ] **Staging Environment**: Deploy to staging environment that mirrors production
- [ ] **Environment Variable Setup**: Configure environment variables in staging
- [ ] **Full Application Testing**: Test ALL core functionality in staging
- [ ] **Performance Validation**: Verify application performance with new configuration
- [ ] **Rollback Testing**: Test rollback procedures in staging environment

### **Phase 4: Production Deployment** ✅

**Before production deployment:**

- [ ] **Production Environment Setup**: Configure environment variables in production
- [ ] **Rollback Commands Ready**: Document and test rollback procedures
- [ ] **Team Coordination**: Ensure team is available for deployment support
- [ ] **Communication Plan**: Notify stakeholders of deployment window
- [ ] **Monitoring Ready**: Have monitoring and alerting configured for deployment

## **Environment Variable Implementation Standards**

### **Code Standards**

**✅ CORRECT - With Appropriate Fallbacks:**
```python
# Development-friendly with fallback
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-development-fallback-key')

# Database with development fallback
'PASSWORD': os.environ.get('DB_PASSWORD', '264537')  # Use actual dev password as fallback

# Debug mode with environment control
DEBUG = os.environ.get('DEBUG', 'True').lower() == 'true'
```

**❌ INCORRECT - No Fallbacks (Breaks Development):**
```python
# This will break development if environment variable is missing
SECRET_KEY = os.environ['SECRET_KEY']  # KeyError if missing
'PASSWORD': os.environ['DB_PASSWORD']  # KeyError if missing
```

**❌ INCORRECT - Poor Fallbacks:**
```python
# Unsafe fallback for security-sensitive settings
SECRET_KEY = os.environ.get('SECRET_KEY', '')  # Empty string is insecure
'PASSWORD': os.environ.get('DB_PASSWORD', '')  # Empty password won't work
```

### **Documentation Standards**

**Required Documentation for Environment Variables:**

1. **Environment Setup Guide** (`ENVIRONMENT_SETUP.md`)
   - Clear step-by-step instructions
   - Example commands for different operating systems
   - Troubleshooting common issues
   - Validation steps to confirm setup

2. **Environment Variable Reference** (in `README.md`)
   - List of all required environment variables
   - Purpose and description of each variable
   - Example values (non-sensitive)
   - Production vs development differences

3. **Emergency Rollback Procedures** (`EMERGENCY_ROLLBACK.md`)
   - Specific git commands for reverting
   - Alternative environment variable setup
   - Validation steps to confirm recovery
   - Contact information for emergency support

## **Emergency Rollback Procedures**

### **Method 1: Git Revert (Preferred)**

```bash
# 1. Clean working directory (handle line ending issues)
git stash

# 2. Revert the problematic commit
git revert [commit_hash] --no-edit

# 3. Verify application recovery
python manage.py runserver

# 4. Confirm application starts successfully
# Visit http://127.0.0.1:8000 to verify functionality
```

### **Method 2: Environment Variable Emergency Setup**

**Windows PowerShell:**
```powershell
$env:DB_PASSWORD="264537"
$env:SECRET_KEY="django-insecure-emergency-key-for-development"
$env:DEBUG="True"
python manage.py runserver
```

**Linux/Mac:**
```bash
export DB_PASSWORD="264537"
export SECRET_KEY="django-insecure-emergency-key-for-development"  
export DEBUG="True"
python manage.py runserver
```

### **Method 3: Create Emergency .env File**

```bash
# Create .env file in project root
echo "DB_PASSWORD=264537" > .env
echo "SECRET_KEY=django-insecure-emergency-key-for-development" >> .env
echo "DEBUG=True" >> .env

# Note: Ensure django-environ is installed and configured to read .env files
```

## **Communication Protocol**

### **Pre-Deployment Communication** (24 hours advance)

**Required Information:**
- List of new environment variables
- Setup instructions and validation steps
- Expected deployment timeline
- Rollback procedures and emergency contacts
- Impact assessment (who needs to take action)

**Communication Channels:**
- Team chat/Slack notification
- Email to all developers
- Documentation updates in repository
- Deployment planning meeting if significant changes

### **Post-Deployment Communication**

**Success Communication:**
- Confirm successful deployment
- Provide updated setup instructions
- Share any lessons learned
- Update documentation with any changes

**Incident Communication:**
- Immediate notification of issues
- Clear description of impact and symptoms
- Rollback procedures being attempted  
- Estimated time for resolution
- Post-incident review and lessons learned

## **Staging Environment Requirements**

### **Staging Environment Must Include:**

- [ ] **Identical Configuration**: Mirror production environment setup
- [ ] **Environment Variables**: Same environment variable requirements as production
- [ ] **Database**: Representative data for realistic testing
- [ ] **Dependencies**: All production dependencies and services
- [ ] **Monitoring**: Logging and monitoring to detect issues

### **Staging Validation Checklist:**

- [ ] **Application Startup**: Verify application starts successfully
- [ ] **Database Connectivity**: Confirm database connections work
- [ ] **Authentication**: Test login/logout functionality
- [ ] **Core Features**: Validate primary application functionality
- [ ] **Performance**: Verify reasonable response times
- [ ] **Error Handling**: Test error scenarios and edge cases

## **Team Training Requirements**

### **All Team Members Must Know:**

1. **Environment Variable Setup**: How to configure required environment variables
2. **Emergency Rollback**: How to quickly revert problematic deployments
3. **Documentation Access**: Where to find setup instructions and emergency procedures
4. **Communication Protocol**: Who to contact and how during incidents
5. **Validation Steps**: How to confirm application is working correctly

### **Training Validation:**

- [ ] **Setup Exercise**: Each team member successfully sets up environment variables
- [ ] **Rollback Exercise**: Each team member successfully performs emergency rollback
- [ ] **Documentation Review**: Team reviews and understands all procedures
- [ ] **Emergency Contact Test**: Verify communication channels work effectively

## **Monitoring and Alerting**

### **Required Monitoring:**

- [ ] **Application Startup**: Alert if application fails to start
- [ ] **Database Connectivity**: Alert if database connections fail
- [ ] **Environment Variables**: Alert if required variables are missing
- [ ] **Security Configuration**: Alert if security settings are misconfigured

### **Response Procedures:**

1. **Immediate Response** (< 5 minutes): Acknowledge alert and assess impact
2. **Diagnosis** (< 15 minutes): Identify root cause and determine resolution approach
3. **Resolution** (< 30 minutes): Apply fix (rollback or environment variable setup)
4. **Validation** (< 45 minutes): Confirm resolution and application functionality
5. **Documentation** (< 24 hours): Update procedures and lessons learned

## **Lessons from SEC-2025-06-02-001 Incident**

### **What Went Wrong:**
- Environment variables deployed without configuration
- No staging environment validation performed
- No rollback procedures documented or tested
- Breaking changes deployed without team coordination
- 5+ hours of complete development blockage

### **Prevention Measures:**
- Mandatory pre-deployment validation checklist
- Required staging environment testing
- Documented and tested rollback procedures
- 24-hour advance notice for environment changes
- Emergency response procedures established

### **Success Factors for Recovery:**
- Git version control enabled rapid rollback
- Clear understanding of problematic commit (841dd3f)
- Simple revert command restored functionality
- Comprehensive incident documentation for learning

**This protocol exists to ensure this type of incident NEVER happens again.** 