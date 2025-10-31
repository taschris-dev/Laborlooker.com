# DocuSign Integration Setup Guide for LaborLooker

## 🔧 **Integration Approach: Public/Remote Signing (RECOMMENDED)**

**Why Public/Remote Signing is Best for LaborLooker:**
- ✅ Mobile-friendly for contractors in the field
- ✅ Professional DocuSign emails build trust
- ✅ Full legal compliance and audit trail
- ✅ Works across all devices and platforms
- ✅ Automatic reminders and notifications
- ✅ Simpler implementation and maintenance

## **Complete Setup Instructions**

### 1. **DocuSign Developer Account Configuration**

**You'll need to provide these credentials in your `.env` file:**

```bash
# DocuSign Configuration (UPDATE THESE VALUES)
DOCUSIGN_INTEGRATION_KEY=your-integration-key-here
DOCUSIGN_USER_ID=your-user-id-here  
DOCUSIGN_ACCOUNT_ID=your-account-id-here
DOCUSIGN_BASE_PATH=https://demo.docusign.net/restapi
DOCUSIGN_OAUTH_BASE_PATH=https://account-d.docusign.com
DOCUSIGN_PRIVATE_KEY_PATH=./docusign_private_key.txt
DOCUSIGN_REDIRECT_URI=http://localhost:5000/docusign/callback
```

### 2. **Step-by-Step DocuSign Setup**

#### A. Create Integration Key
1. Login to your DocuSign Developer Account
2. Go to **Settings** → **Apps and Keys**
3. Click **Add App and Integration Key**
4. Fill in:
   - **App Name**: `LaborLooker Platform`
   - **Description**: `Contract management for LaborLooker job platform`
5. **Save** and copy the **Integration Key** → This goes in `DOCUSIGN_INTEGRATION_KEY`

#### B. Generate RSA Key Pair
1. In your app settings, click **Generate RSA**
2. **Download the private key file** and save it as `docusign_private_key.txt` in your project root
3. Copy the **public key** (will be displayed in DocuSign)

#### C. Set Redirect URI
1. In your app settings, add redirect URI: `http://localhost:5000/docusign/callback`
2. For production: `https://your-domain.com/docusign/callback`

#### D. Get Account Information
1. Go to **Settings** → **API and Keys**
2. Copy your **User ID** → This goes in `DOCUSIGN_USER_ID`
3. Copy your **Account ID** → This goes in `DOCUSIGN_ACCOUNT_ID`
4. Note the **Base URI** (usually `https://demo.docusign.net` for sandbox)

#### E. Grant Consent (Important!)
1. Visit this URL (replace with your Integration Key):
```
https://account-d.docusign.com/oauth/auth?response_type=code&scope=signature%20impersonation&client_id=YOUR_INTEGRATION_KEY&redirect_uri=http://localhost:5000/docusign/callback
```
2. Login and grant consent
3. You'll be redirected to your callback URL

### 3. **Create Contract Templates**

You need to create these templates in your DocuSign account:

#### A. Contractor Agreement Template
1. Go to **Templates** → **Create Template**
2. Upload a contractor agreement document or create from scratch
3. Add these text fields (tags):
   - `contractor_name`
   - `contractor_email`
   - `platform_name`
   - `agreement_date`
   - `project_details`
4. Add signature and date fields for the contractor
5. **Save** with template name: `contractor_agreement_template`

#### B. Client Agreement Template
1. Create another template for client terms
2. Add these text fields:
   - `client_name`
   - `client_email`
   - `platform_name`
   - `agreement_date`
   - `service_description`
3. Add signature fields
4. **Save** with template name: `client_agreement_template`

#### C. Project Contract Template
1. Create template for project-specific contracts
2. Add these text fields:
   - `contractor_name`
   - `client_name`
   - `project_description`
   - `work_request_id`
   - `contract_date`
   - `service_location`
3. Add signature fields for both parties
4. **Save** with template name: `project_contract_template`

### 4. **Environment Setup**

Create or update your `.env` file:

```bash
# Copy from .env.example and update these values:
DOCUSIGN_INTEGRATION_KEY=your-actual-integration-key
DOCUSIGN_USER_ID=your-actual-user-id
DOCUSIGN_ACCOUNT_ID=your-actual-account-id
```

### 5. **Test the Integration**

1. **Install Dependencies**:
```bash
pip install docusign-esign requests python-jose cryptography
```

2. **Run the Application**:
```bash
python app.py
```

3. **Test Contract Creation**:
   - Navigate to `/contracts`
   - Click "New Contract"
   - Fill out the form and submit
   - Check DocuSign for the envelope

### 6. **Webhook Configuration (Optional)**

For production, set up webhooks:

1. In DocuSign, go to **Settings** → **Connect**
2. Add new configuration:
   - **Endpoint URL**: `https://your-domain.com/contracts/webhook`
   - **Events**: Select envelope events (sent, completed, voided)
3. Update `DOCUSIGN_WEBHOOK_SECRET` in your environment

### 7. **Production Considerations**

#### Switch to Production Environment:
```bash
DOCUSIGN_BASE_PATH=https://www.docusign.net/restapi
DOCUSIGN_OAUTH_BASE_PATH=https://account.docusign.com
```

#### Security:
- Keep private key file secure and out of version control
- Use environment variables for all credentials
- Implement proper error handling and logging
- Set up webhook signature verification

### 8. **Pre-Written Contract Documents**

The system includes three pre-written contract types:

1. **Contractor Service Agreement**:
   - Standard terms for contractors
   - Payment and liability clauses
   - Service standards and requirements

2. **Client Terms of Service**:
   - Platform usage terms
   - Privacy and data handling
   - Payment and refund policies

3. **Project-Specific Contracts**:
   - Detailed project scope
   - Timeline and milestones
   - Payment schedule
   - Materials and deliverables

### 9. **Troubleshooting**

**Common Issues:**

1. **Authentication Errors**:
   - Verify Integration Key and User ID
   - Ensure consent has been granted
   - Check private key file path and format

2. **Template Not Found**:
   - Verify template names match exactly
   - Ensure templates are created in the correct account
   - Check template permissions

3. **Webhook Issues**:
   - Verify endpoint URL is accessible
   - Check webhook secret configuration
   - Review DocuSign Connect logs

### 10. **API Endpoints Available**

- `GET /contracts` - Contract dashboard
- `GET /contracts/new` - Create new contract form
- `POST /contracts/new` - Submit new contract
- `GET /contracts/<envelope_id>` - View contract details
- `GET /contracts/<envelope_id>/download` - Download completed PDF
- `POST /contracts/<envelope_id>/void` - Void a contract
- `POST /contracts/webhook` - DocuSign webhook endpoint

### 11. **Why Public/Remote Signing vs Embedded?**

**Public/Remote Signing (Current Implementation):**
- ✅ Better for mobile contractors
- ✅ Professional email workflow
- ✅ Simpler implementation
- ✅ Better legal compliance
- ✅ Works across all platforms

**Embedded Signing (Alternative):**
- ❌ Complex implementation
- ❌ Mobile responsive challenges
- ❌ Session management issues
- ❌ Higher maintenance cost

**Recommendation:** Stay with public/remote signing for optimal contractor/client experience.

### 12. **Privacy Policy & Terms of Use for DocuSign Integration**

#### **A. Privacy Policy Requirements**

**Data Collection & Processing:**
- ✅ Document metadata (creation date, status, participants)
- ✅ Signature data and timestamps
- ✅ Email addresses for contract participants
- ✅ IP addresses for audit trail
- ✅ Device information for security purposes

**Data Sharing:**
- 🔒 **DocuSign Partnership**: Your data is shared with DocuSign under their Business Associate Agreement
- 🔒 **Third-Party Access**: No data shared with unauthorized third parties
- 🔒 **Government Requests**: Only shared when legally required

**Data Retention:**
- 📄 **Signed Contracts**: Retained for 7 years (legal requirement)
- 📄 **Audit Trail**: Maintained for compliance purposes
- 📄 **Personal Data**: Deleted upon account termination (except legal obligations)

**User Rights:**
- 📧 **Access**: Request copies of your signed documents
- ✏️ **Correction**: Update personal information
- 🗑️ **Deletion**: Request account and data deletion
- 📤 **Portability**: Export your contract data

#### **B. Terms of Use for Contract Signing**

**Mandatory Contract Requirements:**
1. **Contractors**: Must sign service agreement before platform access
2. **Clients**: Must accept terms of service before posting work
3. **Project Contracts**: Required for work requests over $500

**Electronic Signature Consent:**
- ✅ By using LaborLooker, you consent to electronic signatures
- ✅ Electronic signatures have same legal effect as handwritten signatures
- ✅ You can request paper copies at any time
- ✅ You can withdraw consent (but may lose platform access)

**Contract Validity:**
- 📋 Contracts are legally binding when all parties sign
- 📋 Voided contracts have no legal effect
- 📋 Disputes resolved through arbitration clause
- 📋 Applicable state and federal laws apply

#### **C. GDPR & CCPA Compliance**

**For EU Users (GDPR):**
- 🇪🇺 **Lawful Basis**: Contract performance and legitimate interests
- 🇪🇺 **Data Controller**: LaborLooker LLC
- 🇪🇺 **Data Processor**: DocuSign Inc.
- 🇪🇺 **Rights**: Access, rectification, erasure, portability, restriction
- 🇪🇺 **DPO Contact**: privacy@laborlooker.com

**For California Users (CCPA):**
- 🏛️ **Personal Information**: Collected for business purposes only
- 🏛️ **Sale of Data**: We do not sell personal information
- 🏛️ **Right to Know**: Request information about data collection
- 🏛️ **Right to Delete**: Request deletion of personal information
- 🏛️ **Non-Discrimination**: No discrimination for exercising rights

#### **D. Security & Data Protection**

**Technical Safeguards:**
- 🔐 **Encryption**: All data encrypted in transit and at rest
- 🔐 **Access Controls**: Role-based access to contract data
- 🔐 **Audit Logging**: All access and modifications logged
- 🔐 **Backup & Recovery**: Regular backups with secure storage

**Organizational Safeguards:**
- 👥 **Staff Training**: Regular privacy and security training
- 👥 **Access Limitation**: Minimum necessary access principle
- 👥 **Background Checks**: For employees handling sensitive data
- 👥 **Incident Response**: Documented breach response procedures

#### **E. User Consent & Notifications**

**Required Consent Messages:**

1. **Before First Contract Signing:**
```
"By proceeding, you consent to electronic signatures and agree that 
electronic signatures have the same legal effect as handwritten signatures. 
You also consent to receive contract-related communications via email."
```

2. **Privacy Notice:**
```
"Your contract data will be processed by LaborLooker and DocuSign to 
facilitate contract management. See our Privacy Policy for full details 
about how your data is collected, used, and protected."
```

3. **Data Sharing Notice:**
```
"Contract information will be shared with relevant parties (contractors, 
clients, platform administrators) as necessary for service delivery and 
legal compliance."
```

#### **F. Legal Disclaimers**

**Platform Liability:**
- ⚖️ LaborLooker facilitates contracts but is not a party to them
- ⚖️ Users responsible for contract terms and performance
- ⚖️ Platform provides technology only, not legal advice
- ⚖️ Maximum liability limited to platform fees paid

**DocuSign Integration:**
- 📝 DocuSign terms and privacy policy also apply
- 📝 Technical issues with DocuSign may affect service
- 📝 Alternative signing methods available upon request
- 📝 Platform not liable for DocuSign service interruptions

#### **G. Implementation Requirements**

**Required Legal Pages:**
1. **Privacy Policy** (`/privacy-policy`)
2. **Terms of Service** (`/terms-of-service`)
3. **Cookie Policy** (`/cookie-policy`)
4. **Data Protection Notice** (`/data-protection`)

**Required Consent Checkboxes:**
- ☑️ Electronic signature consent
- ☑️ Privacy policy acceptance
- ☑️ Terms of service agreement
- ☑️ Email communication consent

**Required User Controls:**
- ⚙️ Privacy settings page
- ⚙️ Data export functionality
- ⚙️ Account deletion option
- ⚙️ Communication preferences

#### **H. Regular Compliance Reviews**

**Monthly Tasks:**
- 📊 Review data processing activities
- 📊 Check consent records
- 📊 Update privacy notices if needed
- 📊 Monitor third-party compliance

**Annual Tasks:**
- 📋 Privacy impact assessment
- 📋 Update legal agreements
- 📋 Staff training updates
- 📋 Security audit and testing

---

## ✅ **What You Need to Provide**

**Required Information:**
1. **Integration Key** from DocuSign app settings
2. **User ID** from DocuSign account settings  
3. **Account ID** from DocuSign account settings
4. **Private key file** downloaded from DocuSign (save as `docusign_private_key.txt`)

**Once you provide these credentials, the DocuSign integration will be fully functional!**