# SQL Database Setup voor Fraude Detectie

Deze applicatie gebruikt Azure SQL Database om artsen te valideren en fraude te detecteren.

## Database Configuratie

### Authenticatie met Entra ID (Azure AD)

De applicatie gebruikt **Entra ID (Azure Active Directory) authenticatie** voor veilige toegang tot de database. Dit is veiliger dan SQL-authenticatie omdat:
- Geen wachtwoorden opgeslagen hoeven te worden
- Gebruik van Azure managed identities
- Automatische token rotation
- Centraal identity management

### Omgevingsvariabelen

Configureer de volgende variabelen in `api/local.settings.json`:

```json
{
  "SQL_SERVER": "sql-demo-server-sociale-fraude.database.windows.net",
  "SQL_DATABASE": "sql-demo-database-sociale-fraude"
}
```

⚠️ **BELANGRIJK**: Geen SQL_USERNAME of SQL_PASSWORD meer nodig! De applicatie gebruikt automatisch uw Azure AD credentials.

### Azure SQL Server Configuratie

1. **Entra ID Admin Instellen**:
   - Ga naar Azure Portal → SQL Server
   - Onder "Settings" → "Microsoft Entra ID"
   - Klik "Set admin" en selecteer uw Azure AD gebruiker of groep

2. **Firewall Regels**:
   - Voeg uw lokale IP-adres toe aan de firewall regels
   - Of schakel "Allow Azure services and resources to access this server" in

3. **Database Toegang**:
   - Zorg dat uw Azure AD account toegang heeft tot de database
   - Gebruik Azure AD authentication in SQL Server Management Studio om in te loggen

### Database Schema

De applicatie gebruikt de volgende tabel:

```sql
CREATE TABLE dbo.doctors_riziv (
    riziv_number NVARCHAR(20) PRIMARY KEY NOT NULL,
    first_name NVARCHAR(100) NULL,
    last_name NVARCHAR(100) NULL,
    specialization NVARCHAR(200) NULL,
    practice_address NVARCHAR(500) NULL,
    postal_code NVARCHAR(10) NULL,
    city NVARCHAR(100) NULL,
    province NVARCHAR(100) NULL,
    phone NVARCHAR(50) NULL,
    email NVARCHAR(200) NULL,
    registration_date DATE NULL,
    is_active BIT NULL
);
```

### Azure AD Gebruiker Toevoegen aan Database

Na het aanmaken van de tabel, moet u uw Azure AD gebruiker toegang geven:

```sql
-- Verbind met de database via Azure AD authenticatie
-- Voer dit uit als database admin

-- Voeg Azure AD gebruiker toe
CREATE USER [your-email@domain.com] FROM EXTERNAL PROVIDER;

-- Geef permissions
ALTER ROLE db_datareader ADD MEMBER [your-email@domain.com];
ALTER ROLE db_datawriter ADD MEMBER [your-email@domain.com];
```

### Voorbeelddata

```sql
-- Actieve arts
INSERT INTO dbo.doctors_riziv 
    (riziv_number, first_name, last_name, specialization, practice_address, city, postal_code, is_active)
VALUES 
    ('12345-67', 'Jan', 'Janssen', 'Huisarts', 'Hoofdstraat 123', 'Brussel', '1000', 1);

-- Inactieve arts
INSERT INTO dbo.doctors_riziv 
    (riziv_number, first_name, last_name, specialization, is_active)
VALUES 
    ('11111-11', 'Pieter', 'Peters', 'Gepensioneerd', 0);
```

## Hoe het werkt

1. **Document Upload**: Gebruiker uploadt een afwezigheidsattest
2. **Content Understanding**: Document wordt geanalyseerd door Azure AI
3. **Extractie**: Artsgegevens worden geëxtraheerd:
   - DoctorName (bijv. "Dr. Jan Janssen")
   - DoctorRizivNumber (bijv. "12345-67")
   - DoctorAddress, DoctorPostalCodeCity, DoctorPhoneNumber
4. **Database Validatie**: Multi-strategie zoeken:
   - **Primair**: Exact match op RIZIV nummer
   - **Fallback**: Fuzzy match op naam + locatie
5. **Fraude Detectie**:
   - **Gevonden in database** → Document geldig ✅
   - **NIET gevonden** → FRAUDE GEDETECTEERD 🚨 → Document afgekeurd ❌

## Validatie Logica

De functie `validate_doctor_in_database()` voert een **twee-stappen validatie** uit:

### Stap 1: RIZIV Nummer Verificatie (Primair)
- ✅ **Gevonden**: RIZIV nummer bestaat in `dbo.doctors_riziv` → **GELDIG**
- ❌ **Niet Gevonden**: Ga naar Stap 2

### Stap 2: Naam + Locatie Verificatie (Fallback)
- Zoek op achternaam in database
- Verfijn met stad/adres indien beschikbaar
- ✅ **Gevonden**: Arts bestaat met matching naam/locatie → **GELDIG**
- ❌ **Niet Gevonden**: Geen match → **🚨 FRAUDE**

### Fraude Detectie
Als de arts **op geen enkele manier** gevonden kan worden in de database:
- 🚫 Document wordt **onmiddellijk afgewezen**
- ⚠️ Status: **"AFGEKEURD - FRAUDE"**
- 📝 Bericht: "FRAUDE GEDETECTEERD: Arts niet gevonden in geregistreerde artsendatabase"

### Mapping: Content Understanding → Database

De extractie van Content Understanding wordt gemapt naar database kolommen:

| Content Understanding Field | Database Column | Gebruikt voor |
|----------------------------|-----------------|---------------|
| `DoctorRizivNumber` | `riziv_number` | Primaire zoeksleutel |
| `DoctorName` | `first_name` + `last_name` | Fallback zoeken |
| `DoctorAddress` | `practice_address` | Locatie verificatie |
| `DoctorPostalCodeCity` | `city` + `postal_code` | Locatie verificatie |
| `DoctorPhoneNumber` | `phone` | (Niet gebruikt in validatie) |

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

### Azure AD Authentication Errors

Als je authenticatie fouten krijgt:

1. **Login met Azure CLI**:
   ```powershell
   az login
   ```

2. **Controleer je account**:
   ```powershell
   az account show
   ```

3. **Zorg dat je account SQL permissions heeft** (zie Azure AD Gebruiker Toevoegen sectie hierboven)

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

## Security Best Practices

✅ **Gebruikt**: Entra ID (Azure AD) authenticatie met DefaultAzureCredential
- Geen wachtwoorden in configuratie
- Automatische token rotation
- Managed identities voor productie

❌ **Vermijd**: SQL authenticatie met username/password
- Risico van gelekte credentials
- Handmatig wachtwoord beheer
- Minder veilig
