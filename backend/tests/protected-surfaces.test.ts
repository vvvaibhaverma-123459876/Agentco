import { ProtectedSurfaceEnforcerService } from './src/services/protected-surface-enforcer.service';
import { db } from './src/db/client';

async function testProtectedSurfaces() {
  console.log('\n' + '='.repeat(70));
  console.log('TESTING: Protected Surface Enforcer Service');
  console.log('='.repeat(70));

  const enforcer = new ProtectedSurfaceEnforcerService();

  // Check what was auto-derived
  const surfaces = enforcer.getProtectedSurfaces();
  console.log(`\nAuto-derived ${surfaces.length} protected surfaces from policy.py:`);
  for (const surface of surfaces) {
    console.log(`  - ${surface}`);
  }

  // Verify existence
  console.log('\nVerifying protected surfaces exist:');
  const state = await enforcer.verifyProtectedSurfacesExist();

  console.log(`\nResults:`);
  console.log(`Total surfaces: ${state.surfaces.length}`);
  console.log(`All exist: ${state.all_exist}`);

  for (const surface of state.surfaces) {
    const status = surface.exists ? '✅' : '❌';
    const hash = surface.content_hash ? `hash=${surface.content_hash.substring(0, 8)}...` : 'N/A';
    console.log(`${status} ${surface.path}`);
    if (surface.exists) {
      console.log(`   ${hash}`);
    }
  }

  // Test modification evaluation
  console.log('\n\nTesting modification attempt evaluation:');
  const protectedPath = '/Users/Zet/agentco/calibration/evidence/evidence_kernel.py';
  const result = await enforcer.evaluateModificationAttempt(
    protectedPath,
    'attempt to modify protected surface',
    'critical'
  );

  console.log(`\nAttempt to modify: ${result.surface_path}`);
  console.log(`Requires human approval: ${result.requires_human_approval}`);

  // Test audit trail recording
  console.log('\n\nRecording surface verification to audit trail...');
  await enforcer.recordSurfaceVerification(state);
  console.log('✅ Recorded to autonomy_memory');

  // Retrieve from DB
  const latest = await enforcer.getLatestSurfaceState();
  if (latest) {
    console.log(`✅ Retrieved from DB: ${latest.surfaces.length} surfaces, all_exist=${latest.all_exist}`);
  }

  console.log('\n' + '='.repeat(70));
  if (state.all_exist) {
    console.log('✅ SUCCESS: All 4 protected surfaces exist and verified');
  } else {
    const missing = state.surfaces.filter(s => !s.exists).map(s => s.path);
    console.log(`❌ FAILURE: Missing surfaces: ${missing.join(', ')}`);
  }
  console.log('='.repeat(70) + '\n');

  await db.end();
}

testProtectedSurfaces().catch(error => {
  console.error('\n❌ Test failed:', error);
  process.exit(1);
});
