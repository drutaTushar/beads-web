# Markdown Import Format Guide for LLMs

This guide explains the markdown format for bulk importing issues into AiTrac. Use this format when creating feature plans, project structures, or task breakdowns.

## Format Overview

The markdown file must contain two main sections:
1. **Issues Structure** - Hierarchical list of issues with metadata
2. **Detailed Content** - Extended descriptions and specifications (optional)

## Basic Structure

```markdown
# Issues Structure
- [logical_id] Issue Title, parameter=value, parameter=value
    - [child_id] Child Issue Title, parameter=value
        - [grandchild_id] Nested Child, parameter=value

# Detailed Content
## logical_id
### description
Content here (max 500 chars)

### design
Design details (max 1000 chars)

### acceptance_criteria
- [ ] Criteria item (max 800 chars total)

### notes
Working notes (max 400 chars)
```

## Issues Structure Section

### Hierarchy Rules
- Use indentation (4 spaces) to show parent-child relationships
- Maximum nesting depth: 3 levels (Epic → Feature → Task)
- Each issue starts with `- [logical_id] Title`

### Logical IDs
- Use lowercase letters, numbers, and underscores only
- Must be unique across the entire file
- Examples: `auth_system`, `user_login`, `api_v2`

### Issue Titles
- **Limit: 100 characters maximum**
- Be concise but descriptive
- Examples: "User Authentication System", "Database Migration Tool"

### Parameters
Add parameters after the title, separated by commas:

#### Required Parameters
- `t=Type` - Issue type (Epic, Feature, Task, Bug, Chore)

#### Optional Parameters
- `p=Priority` - Priority level (0=critical, 1=high, 2=normal, 3=low)
- `assignee=username` - Assigned developer
- `est=minutes` - Estimated time in minutes
- `deps=[id1,id2]` - **Blocking dependencies only** (do NOT include parent in deps)

### ⚠️ Important: Dependency vs Hierarchy Semantics

**Hierarchical relationships** are created automatically from indentation:
```markdown
- [epic1] My Epic, t=Epic
    - [task1] Child Task, t=Task    # Creates PARENT_CHILD dependency automatically
```

**Blocking dependencies** use the `deps=[]` parameter for cross-hierarchy dependencies:
```markdown
- [feature1] Feature One, t=Feature
- [feature2] Feature Two, t=Feature, deps=[feature1]  # feature2 BLOCKS on feature1
```

**❌ WRONG - Don't list parent in deps:**
```markdown
- [epic1] My Epic, t=Epic
    - [task1] Child Task, deps=[epic1]  # REDUNDANT - hierarchy already creates this
```

**✅ CORRECT - Use deps for blocking only:**
```markdown
- [epic1] My Epic, t=Epic
    - [task1] Database Setup, t=Task
    - [task2] API Implementation, t=Task, deps=[task1]  # task2 blocks on task1
```

### Type Hierarchy Rules
**Valid parent → child relationships:**
- Epic → Feature, Task, Bug, Chore
- Feature → Task, Feature
- Task → Task, Chore
- Bug → Task
- Chore → Task, Chore

### Example Issues Structure
```markdown
# Issues Structure
- [platform] Platform Foundation, t=Epic, p=0
    - [auth] Authentication Service, t=Feature, p=0, assignee=john
        - [oauth] OAuth Implementation, t=Task, p=0, est=480
        - [jwt] JWT Token Management, t=Task, p=1, est=240, deps=[oauth]  # jwt blocks on oauth
    - [api] REST API Framework, t=Feature, p=1
        - [routes] API Routes, t=Task, p=0, est=360
        - [validation] Input Validation, t=Task, p=1, est=180, deps=[routes]  # validation blocks on routes
- [docs] Documentation, t=Chore, p=2, deps=[auth,api], est=120  # docs blocks on both auth and api features
```

**What this creates:**
- **Hierarchy**: `platform` → `auth` → `oauth`, `jwt` (PARENT_CHILD relationships)
- **Hierarchy**: `platform` → `api` → `routes`, `validation` (PARENT_CHILD relationships)  
- **Blocking**: `jwt` blocks on `oauth` (BLOCKS relationship)
- **Blocking**: `validation` blocks on `routes` (BLOCKS relationship)
- **Blocking**: `docs` blocks on `auth` and `api` (BLOCKS relationships)

## Detailed Content Section (Optional)

Add detailed specifications using issue logical IDs as section headers.

### Content Fields
Each field has character limits to keep files manageable:

#### description (Max 500 characters)
```markdown
## logical_id
### description
Brief description of what this issue accomplishes. Focus on the "what" and "why".
Keep it concise - detailed specs go in design section.
```

#### design (Max 1000 characters)
```markdown
### design
Technical approach, architecture decisions, API specs, or implementation details.
Can include:
- Architecture overview
- Key components
- API endpoints
- Data models
```

#### acceptance_criteria (Max 800 characters total)
```markdown
### acceptance_criteria
- [ ] Specific, testable criteria
- [ ] User can authenticate via OAuth
- [ ] API returns proper error codes
- [ ] Performance meets requirements
```

#### notes (Max 400 characters)
```markdown
### notes
Implementation notes, considerations, or reminders.
Keep brief - focus on key insights or blockers.
```

## Complete Example

```markdown
# Issues Structure
- [user_system] User Management System, t=Epic, p=0
    - [auth] Authentication, t=Feature, p=0, assignee=alice
        - [login] User Login, t=Task, p=0, est=240
        - [logout] User Logout, t=Task, p=1, est=120, deps=[login]  # logout blocks on login
    - [profile] User Profiles, t=Feature, p=1, deps=[auth]  # profile blocks on auth feature
        - [view_profile] View Profile, t=Task, p=1, est=180
        - [edit_profile] Edit Profile, t=Task, p=1, est=240, deps=[view_profile]  # edit blocks on view
- [testing] Test Suite, t=Chore, p=2, deps=[auth,profile], est=360  # testing blocks on both features

# Detailed Content
## user_system
### description
Complete user management system with authentication, profiles, and preferences. Provides foundation for all user-related features.

### acceptance_criteria
- [ ] Users can register and login
- [ ] Profile management works
- [ ] Secure authentication implemented
- [ ] All user data properly validated

## auth
### description
Secure authentication system supporting multiple login methods.

### design
**Components:**
- OAuth2 integration (Google, GitHub)
- JWT token management
- Session handling
- Password reset flow

**Security:**
- Rate limiting on auth endpoints
- Secure password hashing
- CSRF protection

### acceptance_criteria
- [ ] OAuth2 providers working
- [ ] JWT tokens issued correctly
- [ ] Password reset functional
- [ ] Rate limiting active

## login
### description
User login functionality with email/password and OAuth options.

### design
Login form with validation, error handling, and redirect logic.
Supports: email/password, Google OAuth, GitHub OAuth.

### notes
Consider remember-me functionality for future iteration.
```

## Validation Rules

The parser will validate:
- **Unique logical IDs** across all issues
- **Valid type hierarchy** (Epic can't be child of Task)
- **Dependency references** (deps must refer to existing issues)
- **Circular dependencies** (A→B→C→A not allowed)
- **Character limits** on all text fields

## Best Practices for LLMs

1. **Start with Epic-level structure** - Define 2-4 main epics
2. **Break epics into features** - 3-8 features per epic
3. **Create actionable tasks** - Tasks should be implementable in 1-8 hours
4. **Use consistent naming** - Logical IDs should follow project conventions
5. **Set realistic estimates** - 30-480 minutes per task typical
6. **Consider dependencies** - Order work logically
7. **Stay within limits** - Respect character limits to keep files manageable
8. **Focus on MVP** - Include only essential features in initial plan

## Character Limits Summary
- **Title**: 100 characters
- **Description**: 500 characters  
- **Design**: 1000 characters
- **Acceptance Criteria**: 800 characters total
- **Notes**: 400 characters

These limits ensure the resulting file remains readable and the import process is efficient.