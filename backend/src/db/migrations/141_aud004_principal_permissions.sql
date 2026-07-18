-- Migration 141 (AUD-004 M3): credential-bound RBAC for privileged civilization surfaces.
--
-- Additive. Seeds the permissions the privileged routes require and grants them to roles, so
-- authorization can be resolved against an AUTHENTICATED principal (verifyAuthority) rather than
-- a caller-supplied actor label. Does not weaken existing permissions.

INSERT INTO permissions (name, description, protected_surface) VALUES
  ('judiciary.case.open',     'Open a judiciary case',                     'judiciary_case'),
  ('judiciary.ruling.issue',  'Issue a trial ruling',                      'judiciary_ruling'),
  ('judiciary.appeal.decide', 'Decide an appeal as an independent authority', 'judiciary_appeal'),
  ('evolution.evaluate',      'Independently evaluate a change candidate',  'evolution_evaluation'),
  ('evolution.approve',       'Approve a change promotion',                 'evolution_approval'),
  ('treasury.penalty.impose', 'Impose a treasury penalty',                  'treasury_penalty'),
  ('capability.expand',       'Approve a capability expansion',             'capability_expansion'),
  ('governance.vote',         'Cast a governance vote',                     'governance_vote')
ON CONFLICT (name) DO NOTHING;

INSERT INTO role_permissions (role_id, permission_id, scope)
SELECT r.id, p.id, '*'
  FROM roles r, permissions p
 WHERE (r.role_name, p.name) IN (
   ('governor', 'judiciary.appeal.decide'),
   ('governor', 'judiciary.ruling.issue'),
   ('governor', 'evolution.approve'),
   ('governor', 'evolution.evaluate'),
   ('governor', 'treasury.penalty.impose'),
   ('governor', 'capability.expand'),
   ('governor', 'governance.vote'),
   ('auditor',  'evolution.evaluate'),
   ('claim_maker',   'judiciary.case.open'),
   ('task_executor', 'judiciary.case.open'),
   ('task_executor', 'governance.vote')
 )
ON CONFLICT (role_id, permission_id, scope) DO NOTHING;
