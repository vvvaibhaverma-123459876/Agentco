-- Migration 144 (AUD-004): credential-bound RBAC for the governed capability runtime.
--
-- Additive. The `/v1/capabilities/execute*` and `/v1/capabilities/attempts/:id/cancel` routes
-- (added by the governed-capability-runtime work, merged after the initial AUD-004 route
-- inventory) accepted a caller-supplied `actor.id` and even a caller-supplied
-- `authorization_context.permissions` array with no credential verification -- the same
-- untrusted-body-identity pattern AUD-004 exists to close. Seeds the permissions those routes
-- now require via `requirePrincipal`, so authorization is resolved against an AUTHENTICATED
-- principal rather than a caller-declared claim. Does not weaken existing permissions.

INSERT INTO permissions (name, description, protected_surface) VALUES
  ('capability.execute', 'Execute a governed capability request', 'capability_runtime'),
  ('capability.cancel',  'Cancel a governed capability attempt',  'capability_runtime')
ON CONFLICT (name) DO NOTHING;

INSERT INTO role_permissions (role_id, permission_id, scope)
SELECT r.id, p.id, '*'
  FROM roles r, permissions p
 WHERE (r.role_name, p.name) IN (
   ('task_executor',         'capability.execute'),
   ('task_executor',         'capability.cancel'),
   ('governor',              'capability.execute'),
   ('governor',              'capability.cancel'),
   ('civilization_operator', 'capability.execute'),
   ('civilization_operator', 'capability.cancel')
 )
ON CONFLICT (role_id, permission_id, scope) DO NOTHING;
