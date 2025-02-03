# Modbus Data Logger

This project implements a Modbus data logger system using Docker containers for monitoring environmental sensors.

## 1. System Overview

The system consists of three main components:
- Modbus Logger (Python application)
- PostgreSQL Database
- Grafana Dashboard

### 1.1 Hardware Requirements
- Raspberry Pi or similar device
- USB-RS485 adapter
- Modbus RTU devices (supported sensors)

### 1.2 Software Components
- Docker and Docker Compose
- Python-based Modbus logger
- PostgreSQL database
- Grafana visualization

## 2. Configuration

### 2.1 Sensor Configuration
Sensors are configured in `sensor_metadata.csv` with the following format:
```csv
ID,db-name,data_type,type,unit,signed,registers,value
```

Each sensor requires:
- Unique Modbus ID
- Database column name
- Data type for database
- Sensor type (e.g., temperature, humidity) for own reference
- Unit of measurement (e.g., °C, %) for own reference
- Register configuration (signed, number of registers, value type)

Value types can be one ore multiple adressess of one format (e.g., 16bit, 32bit, 64bit) and make calculations with the values. The registers get read from the Modbus device and afterwards the value is calculated. This is done with the eval function in the python script. So be careful with the syntax.

To get a 32bit value from two 16bit registers, number of registers should be 2 and for 64bit value from four 16bit registers, number of registers should be 4.

### 2.2 Environment Settings
Key settings in docker-compose.yml:
- Data collection interval (INTERVAL=10 seconds)
- Database credentials
- Grafana admin settings
- Time zone (Europe/Berlin)

## 3. Installation

### 3.1 Docker Installation
1. Clone the repository
2. Navigate to the project directory
3. Start the system:
```bash
docker-compose up -d
```

### 3.2 Balena Installation
1. Create a Balena account
2. Install Balena CLI
3. Deploy using:
```bash
balena push <device-name>
```

## 4. Access and Monitoring

### 4.1 Grafana Dashboard
- Access URL: http://<device-ip>:80
- Default credentials:
  - Username: admin
  - Password: changeme1

## 5. Project Structure
```
modbuslogger/
├── docker-compose.yml
├── grafana
│   ├── Dockerfile
│   ├── dashboards
│   │   └── main-dashboard.json
│   └── provisioning
│       ├── dashboards
│       │   └── main.yaml
│       └── datasources
│           └── external-db.yaml
├── modbuslogger
│   ├── Dockerfile
│   ├── modbuslogger.py
│   └── sensor_metadata.csv
├── postgres
│   ├── Dockerfile
│   └── init-scripts
│       └── 01-create-users.sql
└── readme.md
```


## 6. Troubleshooting

1. Check device connectivity using the auto-detection feature
2. Verify Modbus ID assignments
3. Monitor system logs:
```bash
docker-compose logs -f
```

## 7. Security Notes

- Change default passwords in production
- Restrict network access
- Regular backup of configuration and data

## 8. ModbusLogger Script Structure

The `modbuslogger.py` script is built around a `DataLogger` class that handles all Modbus communication and data logging operations.

### 8.1 Main Components

1. **DataLogger Class**
   - Handles metadata loading from CSV
   - Manages Modbus instrument connections
   - Processes register readings and value calculations
   - Handles database operations

For testing, you can set a toggle to print the output and a toggle to only display the SQL query without writing it to the database. These options are in the init section of the class. By default, both options are set to false and only some init statements and errors get printed.

2. **Key Functions**
   - `_load_metadata()`: Reads sensor configuration from CSV
   - `_read_register()`: Handles Modbus register reading with error handling
   - `_evaluate_formula()`: Calculates final values using register data
   - `write_to_database()`: Stores readings in PostgreSQL

3. **Modbus Communication**
   - Auto-detection of USB-RS485 adapters
   - Support for multiple register types (16bit, 32bit)
   - Configurable communication parameters (baudrate: 9600, bytesize: 8, parity: none)

4. **Error Handling**
   - Retry mechanism for failed readings
   - Connection error management
   - Database transaction safety

### 8.2 Execution Flow

1. Load sensor configuration from CSV
2. Auto-detect Modbus device port
3. Initialize database tables
4. Start continuous reading loop:
   - Read values from sensors
   - Process according to formulas
   - Write to database
   - Wait for next interval

The script runs in a continuous loop with configurable intervals (default: 10 seconds) and can be controlled through environment variables in the docker-compose file.
