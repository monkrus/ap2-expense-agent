# Claude Code Subagent Guide

## How Subagents Work

**Important:** Subagents are **NOT automatic or periodic**. They are invoked by Claude during conversations based on:

1. **Proactive (Automatic):** Claude detects context and invokes automatically
   - Example: You modify AP2 code → Claude runs `reviewer` agent

2. **Manual (On-Demand):** You explicitly request an agent
   - Example: You say "Run the billing audit" → Claude runs `billing-usage-auditor`

3. **NOT Scheduled:** Agents do NOT run on timers, cron jobs, or in the background

---

## 🚀 When to Use Each Agent

### Development Phase:
- **backend-tester** → After any backend code changes (automatic)
- **frontend-tester** → After React component changes (automatic)
- **database-migrator** → When modifying models/schema (automatic)

### Feature Completion:
- **expense-flow-validator** → After expense workflow changes (automatic)
- **auth-security-checker** → After auth/security changes (manual)
- **api-integration-tester** → After API integration changes (automatic)
- **reviewer** → After AP2/Marketplace code changes (automatic)

### Optimization Phase:
- **performance-profiler** → When app feels slow or proactive optimization (manual)

### Pre-Deployment:
- **deployment-validator** → Before every production deployment (manual - YOU MUST REQUEST)
- **billing-usage-auditor** → Before billing changes or monthly audit (manual - YOU MUST REQUEST)

---

## 💡 Recommended Agent Workflows

### New Feature Development:
```
1. Write code
2. → backend-tester (automatic - Claude runs after changes)
3. → expense-flow-validator (automatic if expense-related)
4. → reviewer (automatic if AP2-related)
5. → performance-profiler (MANUAL - say "profile performance")
```

### Pre-Production Deployment:
```
YOU MUST SAY: "Validate deployment readiness"

Claude will run:
1. → deployment-validator (environment check)
2. → backend-tester (full test suite)
3. → frontend-tester (build validation)
4. → auth-security-checker (security audit)
5. → performance-profiler (performance baseline)
6. Deploy ✅
```

### Monthly Maintenance:
```
YOU MUST SAY: "Run monthly maintenance audit"

Claude will run:
1. → billing-usage-auditor (revenue reconciliation)
2. → performance-profiler (identify bottlenecks)
3. → database-migrator (check schema drift)
4. → auth-security-checker (security review)
```

---

## 📅 Recommended Maintenance Schedule

**Weekly (Every Monday):**
- Ask Claude: *"Run backend tests and check for any issues"*

**Before Each Deployment:**
- Ask Claude: *"Validate deployment readiness for production"*

**Monthly (1st of each month):**
- Ask Claude: *"Run monthly maintenance audit"*
- Ask Claude: *"Run billing audit for last month"*

**When Performance Issues Occur:**
- Ask Claude: *"Profile the performance of [specific page/endpoint]"*

**After Major Code Changes:**
- Claude will automatically run relevant agents
- You can also request: *"Run full test suite and security audit"*

---

## 🎯 How to Invoke Agents

### Automatic (No action needed):
```
✅ You: "I added a new payment endpoint"
   Claude: *automatically runs reviewer agent*

✅ You: "I modified the expense approval flow"
   Claude: *automatically runs backend-tester and expense-flow-validator*
```

### Manual (You must request):
```
❌ deployment-validator - NOT automatic
✅ You: "Validate deployment readiness"

❌ billing-usage-auditor - NOT automatic
✅ You: "Run billing audit"

❌ performance-profiler - NOT automatic
✅ You: "Profile performance" or "Why is X slow?"
```

---

## 🆘 Quick Commands

Copy-paste these into Claude when needed:

```
# Before deployment
"Validate deployment readiness for production"

# Monthly billing check
"Run billing audit for last month and check for revenue leakage"

# Performance issues
"Profile the performance of the expense list page"

# Security audit
"Run a complete security audit on auth and API endpoints"

# Full health check
"Run all testing agents and provide a full system health report"

# Database check
"Check database migrations and schema consistency"
```
