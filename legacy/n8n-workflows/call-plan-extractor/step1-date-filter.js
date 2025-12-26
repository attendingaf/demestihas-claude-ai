const sevenDaysAgo = new Date();
sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7);
return [{ json: { dateFilter: sevenDaysAgo.toISOString().split('T')[0] } }];
