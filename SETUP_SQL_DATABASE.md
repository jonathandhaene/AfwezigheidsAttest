# SQL Database Setup voor Fraude Detectie

Deze applicatie gebruikt Azure SQL Database om artsen te valideren en fraude te detecteren.

## Database Configuratie

### Omgevingsvariabelen

Configureer de volgende variabelen in `api/local.settings.json`:

```json
{
  "SQL_SERVER": "sql-demo-server-sociale-fraude.database.windows.net",
  "SQL_DATABASE": "sql-demo-database-sociale-fraude",
  "SQL_USERNAME": "CloudSAd4543b78",
  "SQL_PASSWORD": "uw-database-wachtwoord"
}
```

### Database Schema

De applicatie verwacht een tabel met de volgende structuur:

```sql
CREATE TABLE Doctors (
    DoctorID INT PRIMARY KEY IDENTITY(1,1),
    DoctorName NVARCHAR(200) NOT NULL,
    RIZIVNumber NVARCHAR(20),
    IsActive BIT DEFAULT 1,
    IsFraudulent BIT DEFAULT 0,
    CreatedDate DATETIME DEFAULT GETDATE()
);
```

### Voorbeelddata

```sql
-- Geldige arts
INSERT INTO Doctors (DoctorName, RIZIVNumber, IsActive, IsFraudulent)
VALUES ('Dr. Jan Janssen', '12345-67', 1, 0);

-- Frauduleuze arts
INSERT INTO Doctors (DoctorName, RIZIVNumber, IsActive, IsFraudulent)
VALUES ('Dr. Fake Doctor', '99999-99', 1, 1);

-- Inactieve arts
INSERT INTO Doctors (DoctorName, RIZIVNumber, IsActive, IsFraudulent)
VALUES ('Dr. Retired Doctor', '11111-11', 0, 0);
```

## Hoe het werkt

1. **Document Upload**: Gebruiker uploadt een afwezigheidsattest
2. **Content Understanding**: Document wordt geanalyseerd
3. **Arts Extractie**: RIZIV nummer en artsnaam worden geëxtraheerd uit het document
4. **Database Validatie**: Informatie wordt gecontroleerd in SQL Database
5. **Fraude Detectie**: 
   - Als arts als frauduleus staat gemarkeerd → Document wordt AFGEWEZEN
   - Als arts niet actief is → Waarschuwing
   - Als arts niet gevonden is → Melding

## Validatie Logica

De functie `validate_doctor_in_database()` voert de volgende controles uit:

- ✅ **Arts Gevonden**: Doctor bestaat in database
- ⚠️ **Fraude Gedetecteerd**: IsFraudulent = 1 → Document ongeldig
- ⚠️ **Inactief**: IsActive = 0 → Waarschuwing
- ℹ️ **Niet Gevonden**: Arts niet in database → Melding

## RIZIV Nummer Extractie

Het systeem zoekt naar RIZIV nummers in het formaat:
- `RIZIV: 12345-67`
- `RIZIV 12345/67`
- `RIZIV:1234567`

En artsnamen in het formaat:
- `Dr. Jan Janssen`
- `Arts Jan Janssen`
- `Doctor Jan Janssen`

## Troubleshooting

### ODBC Driver Niet Gevonden

Als je de foutmelding krijgt dat de ODBC driver niet gevonden kan worden:

```powershell
# Download en installeer ODBC Driver 18 voor SQL Server
# https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server
```

### Connectie Timeout

Zorg ervoor dat:
1. Je firewall regels correct zijn geconfigureerd in Azure SQL
2. Je lokale IP-adres is toegevoegd aan de firewall regels
3. "Allow Azure services" is ingeschakeld

### Wachtwoord Configuratie

⚠️ **BELANGRIJK**: Vervang `{your_password}` in `local.settings.json` met het echte database wachtwoord.

## Security Best Practices

1. Gebruik nooit credentials in code
2. Bewaar wachtwoorden in Azure Key Vault voor productie
3. Gebruik Managed Identity waar mogelijk
4. `local.settings.json` staat in `.gitignore` (wordt nooit gecommit)
