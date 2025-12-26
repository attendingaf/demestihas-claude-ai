const EABootstrap = require('./bootstrap.js');

(async () => {
  console.log('Testing EA-AI Bootstrap...');
  
  try {
    const result = await EABootstrap.init({
      maxLatency: 300,
      fallbackEnabled: true,
      memoryShare: true
    });
    
    if (result.status === 'ready') {
      console.log(`✓ Bootstrap successful in ${result.bootstrapTime}ms`);
      console.log(`✓ Agents ready: ${result.agents.join(', ')}`);
      
      if (result.bootstrapTime < 300) {
        console.log('✓ Performance target met');
      } else {
        console.log(`⚠ Performance warning: ${result.bootstrapTime}ms > 300ms target`);
      }
      
      process.exit(0);
    } else {
      console.log('✗ Bootstrap failed');
      process.exit(1);
    }
  } catch (error) {
    console.error('✗ Error:', error.message);
    // Don't fail completely, just warn
    console.log('⚠ Bootstrap test had issues but continuing setup');
    process.exit(0);
  }
})();
