from common.db import execute_query

db_sql = """
DROP TABLE IF EXISTS action_requests;
DROP TABLE IF EXISTS devices;
DROP TABLE IF EXISTS iam_accounts;
DROP TABLE IF EXISTS runbook_rules;
DROP TABLE IF EXISTS service_tickets;
DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS vpn_profiles;
CREATE TABLE action_requests (request_id TEXT PRIMARY KEY, user_id TEXT, action_type TEXT, requested_at TEXT, confirmation_status TEXT, execution_status TEXT, evidence_ref TEXT);
INSERT INTO "action_requests" VALUES('AR1001','U7002','Unlock Account','2025-04-10T09:05:00Z','Pending','Not Started','runbook_account_lockout#step_4');
INSERT INTO "action_requests" VALUES('AR1002','U7004','VPN Re-enable','2025-04-10T08:02:00Z','Pending','Blocked - Compliance Check','runbook_vpn_access#step_3');
CREATE TABLE devices (device_id TEXT PRIMARY KEY, user_id TEXT, device_name TEXT, device_type TEXT, os TEXT, encryption_status TEXT, vpn_client_version TEXT, last_seen TEXT);
INSERT INTO "devices" VALUES('D8001','U7001','FIN-NY-2214','Laptop','Windows 11','Compliant','3.8.1','2025-04-10T08:55:00Z');
INSERT INTO "devices" VALUES('D8002','U7002','OPS-DAL-1841','Laptop','Windows 10','Compliant','3.7.9','2025-04-10T09:02:00Z');
INSERT INTO "devices" VALUES('D8003','U7003','ANL-LON-9920','Laptop','Windows 11','Compliant','3.8.1','2025-04-10T07:45:00Z');
INSERT INTO "devices" VALUES('D8004','U7004','CLM-TOR-5531','Laptop','Windows 11','Non-Compliant','3.6.4','2025-04-09T22:14:00Z');
CREATE TABLE iam_accounts (user_id TEXT PRIMARY KEY, directory_account TEXT, account_status TEXT, mfa_enabled TEXT, last_password_change TEXT, failed_login_count INTEGER, locked_until TEXT);
INSERT INTO "iam_accounts" VALUES('U7001','MAYA.PATEL','Active','Yes','2025-03-12',0,NULL);
INSERT INTO "iam_accounts" VALUES('U7002','CARLOS.MENDEZ','Locked','Yes','2025-01-10',7,'2025-04-10T10:00:00Z');
INSERT INTO "iam_accounts" VALUES('U7003','ALINA.NOVAK','Active','Yes','2025-02-18',1,NULL);
INSERT INTO "iam_accounts" VALUES('U7004','NOAH.KIM','Active','No','2024-12-20',2,NULL);
CREATE TABLE runbook_rules (rule_id TEXT PRIMARY KEY, workflow TEXT, required_verification TEXT, confirmation_required TEXT, destructive_action_block TEXT, sla_target TEXT);
INSERT INTO "runbook_rules" VALUES('RB1101','Account Lockout','employee_id + manager_name','Yes','No password reset without confirmation','15 minutes');
INSERT INTO "runbook_rules" VALUES('RB1102','VPN Access','employee_id + device_name','Yes','No VPN enable if device compliance fails','30 minutes');
CREATE TABLE service_tickets (ticket_id TEXT PRIMARY KEY, user_id TEXT, status TEXT, priority TEXT, category TEXT, created_at TEXT, assigned_group TEXT, summary TEXT);
INSERT INTO "service_tickets" VALUES('SD9001','U7002','New','High','Account Lockout','2025-04-10T09:04:00Z','IAM Support','Workstation locked after too many failed attempts.');
INSERT INTO "service_tickets" VALUES('SD9002','U7004','In Progress','High','VPN Access','2025-04-10T07:50:00Z','Network Access','VPN access denied for user connecting from hotel network.');
INSERT INTO "service_tickets" VALUES('SD9003','U7001','Resolved','Medium','Password Reset','2025-04-08T15:12:00Z','IAM Support','Password reset request completed after identity verification.');
CREATE TABLE users (user_id TEXT PRIMARY KEY, employee_id TEXT, full_name TEXT, department TEXT, location TEXT, manager TEXT, email TEXT, status TEXT, identity_verification_level TEXT);
INSERT INTO "users" VALUES('U7001','E10231','Maya Patel','Finance','New York','R. Singh','maya.patel@company.example','Active','Standard');
INSERT INTO "users" VALUES('U7002','E11892','Carlos Mendez','Operations','Dallas','J. Carter','carlos.mendez@company.example','Locked','Standard');
INSERT INTO "users" VALUES('U7003','E12773','Alina Novak','Analytics','London','P. Shah','alina.novak@company.example','Active','High');
INSERT INTO "users" VALUES('U7004','E13554','Noah Kim','Claims','Toronto','T. Wallace','noah.kim@company.example','VPN Suspended','Standard');
CREATE TABLE vpn_profiles (user_id TEXT PRIMARY KEY, vpn_status TEXT, profile_name TEXT, last_successful_login TEXT, certificate_status TEXT, device_compliance TEXT);
INSERT INTO "vpn_profiles" VALUES('U7001','Enabled','Corp-Standard','2025-04-10T08:05:00Z','Valid','Pass');
INSERT INTO "vpn_profiles" VALUES('U7002','Enabled','Corp-Standard','2025-04-09T17:20:00Z','Valid','Pass');
INSERT INTO "vpn_profiles" VALUES('U7003','Enabled','Corp-Restricted','2025-04-10T07:15:00Z','Valid','Pass');
INSERT INTO "vpn_profiles" VALUES('U7004','Denied','Corp-Standard','2025-04-08T19:30:00Z','Expired','Fail');
"""

vector_sql = """
DROP TABLE IF EXISTS documents;
CREATE TABLE documents (document_id TEXT PRIMARY KEY, title TEXT, content TEXT, embedding vector(1024));
"""

single_table_sql = """
CREATE TABLE action_requests (request_id TEXT PRIMARY KEY, user_id TEXT, action_type TEXT, requested_at TEXT, confirmation_status TEXT, execution_status TEXT, evidence_ref TEXT);
"""

def handler(event, context):
    print("Received event: " + str(event))
    # Process the event here
    query_type = event.get('query_type', 'db_sql')
    if query_type == 'db_sql':
        sql = db_sql
    elif query_type == 'vector_sql':
        sql = vector_sql
    elif query_type == 'single_table_sql':
        sql = single_table_sql
    else:
        return {
            'statusCode': 400,
            'body': f'Invalid query_type: {query_type}'
        }
    execute_query(sql)
    return {
        'statusCode': 200,
        'body': 'Hello from Data Seeder Lambda!'
    }