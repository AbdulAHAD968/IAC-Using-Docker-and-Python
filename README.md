# Enhanced Container Management System (CMS) - Infrastructure as Code

A comprehensive Infrastructure as Code (IaC) solution with container orchestration, deployment versioning, security management, and ML-based intrusion detection system (IDS).

## Features

### 1. Container Management
- Deploy and manage Docker containers
- Real-time health monitoring
- Container lifecycle management (create, start, stop, delete)
- Network connectivity testing
- Multi-container orchestration

### 2. Deployment Management
- Version control for deployments
- Configuration versioning with git integration
- Automated rollback capabilities
- Deployment history tracking
- Configuration change detection

### 3. Security Management
- SSH key management and rotation
- Firewall rule configuration
- Security policy enforcement
- Encrypted credential storage
- Access control management

### 4. ML-Based Intrusion Detection System (IDS)
- **Web Server Threat Detection**: Admin access, path traversal, XSS, SQL injection, suspicious tools
- **Database Attack Detection**: SQL injection patterns, dangerous operations, stacked queries
- **Email Threat Detection**: Phishing patterns, spam, malware payloads, suspicious clients
- Hybrid detection: Manual rules + ML model fallback
- Real-time alert generation and reporting

### 5. Health Monitoring
- Continuous system health checks
- CPU, memory, and disk monitoring
- Service availability checks
- Health report generation
- Alert notifications

### 6. Dashboard
- Real-time status monitoring
- Interactive deployment controls
- IDS alert management
- System logs and diagnostics
- Configuration management interface

## Project Structure

```
├── cms/
│   ├── main.py                 # CMS core initialization
│   ├── config_manager.py       # Configuration management
│   ├── deployment_manager.py   # Deployment orchestration
│   ├── security.py             # Security operations
│   ├── enhanced_security.py    # Extended security features
│   ├── health_monitor.py       # Health monitoring system
│   ├── network.py              # Network operations
│   ├── communication.py        # Inter-component communication
│   ├── ids_manager.py          # IDS core with ML models
│   ├── config.yaml             # Configuration file
│   └── config_versions/        # Configuration history
├── models/
│   ├── web_model.pkl           # Web threat ML model
│   ├── db_model.pkl            # Database threat ML model
│   ├── email_model.pkl         # Email threat ML model
│   └── preprocess.py           # Feature extraction
├── templates/
│   └── dashboard.html          # Web dashboard
├── static/
│   ├── css/style.css           # Dashboard styles
│   ├── js/dashboard.js         # Dashboard functionality
│   └── js/ui.js                # UI utilities
├── keys/                       # SSH keys (in .gitignore)
├── scripts/
│   └── deploy_infrastructure.sh # Deployment script
├── health_reports/            # Generated health reports
├── deployments/               # Deployment artifacts
├── enhanced_api.py            # Flask API server
├── docker-compose.yml         # Docker composition
└── requirements.txt           # Python dependencies
```

## Installation

### Prerequisites
- Python 3.8+
- Docker & Docker Compose
- Git
- Virtual Environment (recommended)

### Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd help
```

2. Create and activate virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure the system:
```bash
cp cms/config.yaml.example cms/config.yaml
# Edit config.yaml with your settings
```

5. Deploy infrastructure:
```bash
./scripts/deploy_infrastructure.sh
```

## Usage

### Starting the System

1. Start Docker services:
```bash
docker-compose up -d
```

2. Run the Flask API server:
```bash
python3 enhanced_api.py
```

3. Access the dashboard:
```
http://localhost:5001
```

### Dashboard Operations

#### Deployment Tab
- Deploy complete infrastructure
- Create client containers
- Cleanup all resources
- Check configuration changes
- Redeploy on configuration change
- Test network connectivity

#### Health & Monitoring Tab
- View system health status
- Monitor container resources
- Check service availability
- Download health reports

#### Security Tab
- Manage SSH keys
- Configure firewall rules
- View security policies
- Manage access controls

#### IDS & Threats Tab
- Web Server Tests: Normal Logs, Attack Logs
- Database Tests: Normal Queries, Attack Queries
- Email Server Tests: Normal Emails, Phishing Emails
- View real-time alerts
- Filter and search alerts
- Clear alert history

#### Versioning Tab
- View deployment history
- Compare configurations
- Rollback deployments
- Manage versions

#### Configuration Tab
- Edit system configuration
- Validate configuration
- Apply configuration changes
- View configuration history

## API Endpoints

### IDS Endpoints
- `GET /api/ids/status` - Get IDS status and model information
- `GET /api/ids/alerts` - Get all detected alerts
- `POST /api/ids/analyze` - Analyze a single log entry
- `POST /api/ids/generate-logs` - Generate and analyze normal web logs
- `POST /api/ids/generate-db-logs` - Generate and analyze normal database logs
- `POST /api/ids/generate-email-logs` - Generate and analyze normal email logs
- `POST /api/ids/generate-attacks` - Generate and analyze attack patterns
- `GET /api/ids/test-attack` - Test attack detection

### Deployment Endpoints
- `POST /api/deploy` - Deploy infrastructure
- `GET /api/deployments` - List deployments
- `POST /api/cleanup` - Cleanup resources
- `POST /api/check-config-changes` - Check for configuration changes

### Health Endpoints
- `GET /api/health` - Get overall system health
- `GET /api/health/detailed` - Get detailed health report
- `GET /api/containers` - List all containers
- `GET /api/logs` - Get system logs

### Security Endpoints
- `GET /api/security/keys` - List SSH keys
- `POST /api/security/keys` - Generate new SSH key
- `GET /api/security/firewall` - Get firewall rules
- `POST /api/security/firewall` - Configure firewall rule

## ML Models

The system includes three pre-trained scikit-learn models for threat detection:

### Web Model (IsolationForest)
- Detects: Admin access, command execution, path traversal, XSS, SQL injection, scanner tools
- Confidence: 0.95 for manual rules, variable for ML predictions

### Database Model (RandomForestClassifier)
- Detects: SQL injection, UNION attacks, dangerous operations, stacked queries
- Confidence: 0.95 for manual rules, variable for ML predictions

### Email Model (MultinomialNB)
- Detects: Phishing attempts, spam, malware payloads, suspicious email clients
- Confidence: 0.90 for manual patterns

### Hybrid Detection Approach
- Manual pattern matching for known attacks (fast, 0.95 confidence)
- ML model fallback for anomalous patterns (0.5-0.8 confidence)
- Comprehensive logging of all detection decisions

## Configuration

Edit `cms/config.yaml` to customize:

```yaml
system:
  name: Enhanced CMS
  version: 1.0
  mode: full

deployment:
  auto_redeploy: false
  health_check_interval: 30
  log_level: INFO

security:
  enable_firewall: true
  ssh_key_rotation_days: 90
  enforce_tls: true

ids:
  enable_monitoring: true
  alert_threshold: 0.85
  models_path: ./models
```

## Monitoring & Alerts

### Health Reports
Generated health reports are stored in `health_reports/` with timestamps:
```
health_report_20251128_143022.json
```

### IDS Alerts
All detected threats are logged and can be:
- Viewed in the dashboard
- Filtered by severity and type
- Exported for analysis
- Cleared after review

### Log Files
- `server.log` - Flask API server logs
- `startup.log` - Deployment startup logs
- `deployments/` - Detailed deployment logs

## Development

### Running Tests
```bash
python3 comprehensive_ids_test.py
```

### Code Cleanup
The codebase has been cleaned to remove comments and emojis while maintaining all functionality.

### Adding New Models
1. Place trained model in `models/` directory
2. Update `cms/ids_manager.py` to load the model
3. Add analysis method following the pattern of existing models

## Deployment to GitHub

### Initialize Git Repository
```bash
cd /home/ahad/Desktop/help
git init
git add .
git commit -m "Initial commit: Enhanced CMS with IDS"
git branch -M main
git remote add origin <your-github-repo-url>
git push -u origin main
```

### .gitignore Coverage
The `.gitignore` file excludes:
- Python cache and virtual environments
- Sensitive files (keys, secrets, credentials)
- Generated logs and reports
- Build artifacts
- IDE configurations
- OS-specific files

## Security Notes

- Store sensitive data (SSH keys, credentials) outside the repository
- Use `.env` files for local development (excluded from git)
- Rotate SSH keys regularly
- Keep ML models updated with new threat patterns
- Review and approve all configuration changes before deployment
- Enable firewall rules in production
- Use TLS/HTTPS for all communications

## Troubleshooting

### IDS Models Not Detecting
- Verify model files exist in `models/` directory
- Check scikit-learn version compatibility
- Review alert thresholds in configuration
- Check logs for model loading errors

### Container Deployment Issues
- Verify Docker daemon is running
- Check Docker Compose configuration
- Review deployment logs in `deployments/`
- Ensure sufficient system resources

### Dashboard Access Issues
- Verify Flask server is running on port 5001
- Check firewall rules allowing port 5001
- Review API server logs
- Clear browser cache and refresh

## Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open Pull Request

## License

This project is licensed under the MIT License - see LICENSE file for details.

## Support

For issues, questions, or contributions:
- Create an issue on GitHub
- Contact the development team
- Check the documentation in project root

## Changelog

### Version 1.0 (Current)
- Initial release with full IaC support
- ML-based IDS with 3 pre-trained models
- Comprehensive dashboard
- Security management
- Health monitoring
- Deployment versioning
- Code cleanup (removed comments and emojis)
- GitHub deployment ready

## Roadmap

- Kubernetes support
- Enhanced ML model training
- API authentication and authorization
- Advanced analytics dashboard
- Automated incident response
- Integration with external monitoring tools
- Webhook support for CI/CD
