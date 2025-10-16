"""Tests for the 'Let's Continue' autonomous agent polling protocol

This module tests the complete workflow of autonomous agents:
1. Poll for ready tasks using ready() function
2. Select and start working on tasks
3. Complete tasks and mark them closed
4. Poll again for newly available tasks
5. Validate task sequencing and dependency resolution

Uses markdown import to create complex issue hierarchies in single calls.
"""

import pytest
from unittest.mock import patch
from aitrac.storage.database import reset_database_globals
from aitrac.storage.issue_service import issue_service
from aitrac.storage.dependency_service import dependency_service
from aitrac.storage.markdown_parser import MarkdownParser
from aitrac.api.markdown_import import _import_issues
from aitrac.models import Status, IssueType, DependencyType


class TestLetsContinueProtocol:
    """Test suite for autonomous agent polling protocol"""

    def setup_method(self):
        """Reset database before each test"""
        reset_database_globals()
        
        # Additional cleanup - remove any existing issues
        from aitrac.storage.database import get_db_session
        from aitrac.models import Issue, Dependency, Event
        
        with get_db_session() as session:
            # Delete all dependencies first (foreign key constraints)
            session.query(Dependency).delete()
            # Delete all events  
            session.query(Event).delete()
            # Delete all issues
            session.query(Issue).delete()
            session.commit()
            
        print(f"\n🧹 Database cleaned for test")

    async def import_markdown_issues(self, markdown_content: str):
        """Helper to import issues from markdown and return issue mapping"""
        parser = MarkdownParser()
        result = parser.parse(markdown_content)
        
        if not result.is_valid:
            raise ValueError(f"Invalid markdown: {result.errors}")
        
        # Import issues and get the mapping
        await _import_issues(result.issues)
        
        # Create mapping from logical_id to physical_id
        mapping = {}
        for parsed_issue in result.issues:
            # Find the issue by markdown_id
            issue = issue_service.get_issue_by_markdown_id(parsed_issue.logical_id)
            if issue:
                mapping[parsed_issue.logical_id] = issue.id
        
        return mapping

    def get_ready_tasks(self):
        """Get list of ready tasks (simulates agent polling)"""
        return dependency_service.get_ready_work(limit=50)

    def start_task(self, issue_id: str, agent_name: str = "test_agent"):
        """Mark task as in progress (simulates agent starting work)"""
        return issue_service.start_issue(issue_id, actor=agent_name)

    def complete_task(self, issue_id: str, reason: str = "Task completed", agent_name: str = "test_agent"):
        """Mark task as closed (simulates agent completing work)"""
        return issue_service.close_issue(issue_id, reason=reason, actor=agent_name)

    def get_issue_status(self, issue_id: str):
        """Get current status of an issue"""
        issue = issue_service.get_issue(issue_id)
        return issue.status if issue else None

    def assert_task_sequence(self, expected_sequence, actual_tasks):
        """Assert that ready tasks match expected sequence"""
        actual_ids = [task.id for task in actual_tasks]
        assert len(actual_ids) == len(expected_sequence), f"Expected {len(expected_sequence)} tasks, got {len(actual_ids)}"
        
        for expected_id, actual_id in zip(expected_sequence, actual_ids):
            assert actual_id == expected_id, f"Expected task {expected_id}, got {actual_id}"

    @pytest.mark.asyncio
    async def test_simple_sequential_workflow(self):
        """Test basic sequential task workflow"""
        markdown = """
# Issues Structure
- [setup] Setup Database, t=Task, p=0
- [api] Build API, t=Task, p=1, deps=[setup]
- [ui] Build UI, t=Task, p=2, deps=[api]
- [test] Test Everything, t=Task, p=3, deps=[ui]
"""
        
        # Import issues
        mapping = await self.import_markdown_issues(markdown)
        setup_id = mapping['setup']
        api_id = mapping['api']
        ui_id = mapping['ui']
        test_id = mapping['test']
        
        print(f"\n=== Test: Simple Sequential Workflow ===")
        print(f"Issues: setup={setup_id}, api={api_id}, ui={ui_id}, test={test_id}")
        
        # Step 1: Initial poll - only setup should be ready
        ready_tasks = self.get_ready_tasks()
        print(f"Step 1 - Ready tasks: {[task.id for task in ready_tasks]}")
        assert len(ready_tasks) == 1
        assert ready_tasks[0].id == setup_id
        
        # Step 2: Start and complete setup
        self.start_task(setup_id)
        assert self.get_issue_status(setup_id) == Status.IN_PROGRESS
        
        self.complete_task(setup_id, "Database setup completed")
        assert self.get_issue_status(setup_id) == Status.CLOSED
        
        # Step 3: Poll again - now API should be ready
        ready_tasks = self.get_ready_tasks()
        print(f"Step 3 - Ready tasks: {[task.id for task in ready_tasks]}")
        assert len(ready_tasks) == 1
        assert ready_tasks[0].id == api_id
        
        # Step 4: Start and complete API
        self.start_task(api_id)
        self.complete_task(api_id, "API implementation completed")
        
        # Step 5: Poll again - now UI should be ready
        ready_tasks = self.get_ready_tasks()
        print(f"Step 5 - Ready tasks: {[task.id for task in ready_tasks]}")
        assert len(ready_tasks) == 1
        assert ready_tasks[0].id == ui_id
        
        # Step 6: Complete UI and check test becomes ready
        self.start_task(ui_id)
        self.complete_task(ui_id, "UI implementation completed")
        
        ready_tasks = self.get_ready_tasks()
        print(f"Step 6 - Ready tasks: {[task.id for task in ready_tasks]}")
        assert len(ready_tasks) == 1
        assert ready_tasks[0].id == test_id
        
        # Step 7: Complete test and verify no more tasks
        self.start_task(test_id)
        self.complete_task(test_id, "Testing completed")
        
        ready_tasks = self.get_ready_tasks()
        print(f"Step 7 - Ready tasks: {[task.id for task in ready_tasks]}")
        assert len(ready_tasks) == 0

    @pytest.mark.asyncio
    async def test_parallel_tasks_under_epic(self):
        """Test parallel tasks under an epic"""
        markdown = """
# Issues Structure
- [platform] Platform Foundation, t=Epic, p=0
    - [auth] Authentication Service, t=Feature, p=0
        - [oauth] OAuth Implementation, t=Task, p=0
        - [jwt] JWT Token Management, t=Task, p=1
    - [api] REST API Framework, t=Feature, p=1
        - [routes] API Routes, t=Task, p=0
        - [validation] Input Validation, t=Task, p=1
"""
        
        mapping = await self.import_markdown_issues(markdown)
        oauth_id = mapping['oauth']
        jwt_id = mapping['jwt']
        routes_id = mapping['routes']
        validation_id = mapping['validation']
        
        print(f"\n=== Test: Parallel Tasks Under Epic ===")
        
        # Step 1: Initial poll - leaf tasks should be ready for parallel work
        ready_tasks = self.get_ready_tasks()
        ready_ids = [task.id for task in ready_tasks]
        print(f"Step 1 - Ready tasks: {ready_ids}")
        
        # Should have 4 leaf tasks ready (oauth, jwt, routes, validation)
        assert len(ready_tasks) == 4
        assert oauth_id in ready_ids
        assert jwt_id in ready_ids
        assert routes_id in ready_ids
        assert validation_id in ready_ids
        
        # Step 2: Complete oauth task
        self.start_task(oauth_id)
        self.complete_task(oauth_id, "OAuth completed")
        
        # Step 3: Poll again - should still have 3 remaining tasks
        ready_tasks = self.get_ready_tasks()
        ready_ids = [task.id for task in ready_tasks]
        print(f"Step 3 - Ready tasks: {ready_ids}")
        assert len(ready_tasks) == 3
        assert oauth_id not in ready_ids  # oauth is completed
        assert jwt_id in ready_ids
        assert routes_id in ready_ids
        assert validation_id in ready_ids

    @pytest.mark.asyncio
    async def test_blocking_dependencies_across_features(self):
        """Test blocking dependencies that cross feature boundaries"""
        markdown = """
# Issues Structure
- [platform] Platform Foundation, t=Epic, p=0
    - [auth] Authentication Service, t=Feature, p=0
        - [user_model] User Data Model, t=Task, p=0
        - [login] Login Implementation, t=Task, p=1, deps=[user_model]
    - [api] REST API Framework, t=Feature, p=1
        - [middleware] Auth Middleware, t=Task, p=0, deps=[login]
        - [endpoints] API Endpoints, t=Task, p=1, deps=[middleware]
    - [ui] User Interface, t=Feature, p=2
        - [dashboard] User Dashboard, t=Task, p=0, deps=[endpoints]
"""
        
        mapping = await self.import_markdown_issues(markdown)
        auth_service_id = mapping['auth']
        api_framework_id = mapping['api']
        user_model_id = mapping['user_model']
        login_id = mapping['login']
        middleware_id = mapping['middleware']
        endpoints_id = mapping['endpoints']
        dashboard_id = mapping['dashboard']
        
        print(f"\n=== Test: Blocking Dependencies Across Features ===")
        
        # Step 1: Only user_model should be ready initially
        ready_tasks = self.get_ready_tasks()
        ready_ids = [task.id for task in ready_tasks]
        print(f"Step 1 - Ready tasks: {ready_ids}")
        assert len(ready_tasks) == 1
        assert ready_tasks[0].id == user_model_id
        
        # Step 2: Complete user_model, now login should be ready
        self.start_task(user_model_id)
        self.complete_task(user_model_id, "User model completed")
        
        ready_tasks = self.get_ready_tasks()
        ready_ids = [task.id for task in ready_tasks]
        print(f"Step 2 - Ready tasks: {ready_ids}")
        assert len(ready_tasks) == 1
        assert ready_tasks[0].id == login_id
        
        # Step 3: Complete login, now middleware should be ready
        self.start_task(login_id)
        self.complete_task(login_id, "Login completed")
        
        ready_tasks = self.get_ready_tasks()
        ready_ids = [task.id for task in ready_tasks]
        print(f"Step 3 - Ready tasks: {ready_ids}")
        assert len(ready_tasks) == 2  # Auth Service and Auth Middleware are both ready now
        ready_task_ids = {task.id for task in ready_tasks}
        assert auth_service_id in ready_task_ids  # Auth Service ready (children completed)
        assert middleware_id in ready_task_ids    # Auth Middleware ready (blocker completed)
        
        # Step 4: Complete middleware, now endpoints should be ready
        self.start_task(middleware_id)
        self.complete_task(middleware_id, "Middleware completed")
        
        ready_tasks = self.get_ready_tasks()
        ready_ids = [task.id for task in ready_tasks]
        print(f"Step 4 - Ready tasks: {ready_ids}")
        assert len(ready_tasks) == 2  # Auth Service and API Endpoints are both ready now
        ready_task_ids = {task.id for task in ready_tasks}
        assert auth_service_id in ready_task_ids  # Auth Service ready (children completed)
        assert endpoints_id in ready_task_ids     # API Endpoints ready (blocker completed)
        
        # Step 5: Complete endpoints, now dashboard should be ready
        self.start_task(endpoints_id)
        self.complete_task(endpoints_id, "Endpoints completed")
        
        ready_tasks = self.get_ready_tasks()
        ready_ids = [task.id for task in ready_tasks]
        print(f"Step 5 - Ready tasks: {ready_ids}")
        assert len(ready_tasks) == 3  # Auth Service, REST API Framework, and User Dashboard are ready
        ready_task_ids = {task.id for task in ready_tasks}
        assert auth_service_id in ready_task_ids    # Auth Service ready (all children completed)
        assert api_framework_id in ready_task_ids   # REST API Framework ready (all children completed)
        assert dashboard_id in ready_task_ids       # User Dashboard ready (blocker completed)

    @pytest.mark.asyncio
    async def test_priority_ordering(self):
        """Test that ready tasks are returned in priority order"""
        markdown = """
# Issues Structure
- [critical] Critical Bug Fix, t=Bug, p=0
- [high] High Priority Feature, t=Feature, p=1
- [normal] Normal Task, t=Task, p=2
- [low] Low Priority Chore, t=Chore, p=3
"""
        
        mapping = await self.import_markdown_issues(markdown)
        critical_id = mapping['critical']
        high_id = mapping['high']
        normal_id = mapping['normal']
        low_id = mapping['low']
        
        print(f"\n=== Test: Priority Ordering ===")
        
        # All tasks should be ready, but ordered by priority
        ready_tasks = self.get_ready_tasks()
        ready_ids = [task.id for task in ready_tasks]
        print(f"Ready tasks in order: {ready_ids}")
        
        assert len(ready_tasks) == 4
        
        # Should be ordered by priority (0=critical, 1=high, 2=normal, 3=low)
        self.assert_task_sequence([critical_id, high_id, normal_id, low_id], ready_tasks)
        
        # Verify priorities
        assert ready_tasks[0].priority == 0  # critical
        assert ready_tasks[1].priority == 1  # high
        assert ready_tasks[2].priority == 2  # normal
        assert ready_tasks[3].priority == 3  # low

    @pytest.mark.asyncio
    async def test_complex_dependency_graph(self):
        """Test complex dependency graph with multiple blocking patterns"""
        markdown = """
# Issues Structure
- [foundation] Foundation Epic, t=Epic, p=0
    - [database] Database Setup, t=Task, p=0
    - [config] Configuration, t=Task, p=0
    - [logging] Logging System, t=Task, p=1, deps=[config]
    - [metrics] Metrics Collection, t=Task, p=1, deps=[database,logging]
- [auth_epic] Authentication Epic, t=Epic, p=1
    - [auth_db] Auth Database Schema, t=Task, p=0, deps=[database]
    - [auth_service] Auth Service, t=Task, p=1, deps=[auth_db,logging]
    - [auth_api] Auth API Endpoints, t=Task, p=2, deps=[auth_service,metrics]
- [integration] Integration Tests, t=Task, p=0, deps=[auth_api]
"""
        
        mapping = await self.import_markdown_issues(markdown)
        
        print(f"\n=== Test: Complex Dependency Graph ===")
        
        # Track the complete workflow
        completed_tasks = []
        step = 1
        
        while True:
            ready_tasks = self.get_ready_tasks()
            ready_ids = [task.id for task in ready_tasks]
            
            if not ready_tasks:
                print(f"Step {step} - No more ready tasks. Workflow complete.")
                break
            
            print(f"Step {step} - Ready tasks: {ready_ids}")
            
            # Complete the first ready task (highest priority)
            task_to_complete = ready_tasks[0]
            task_id = task_to_complete.id
            
            # Find logical ID for better logging
            logical_id = None
            for logical, physical in mapping.items():
                if physical == task_id:
                    logical_id = logical
                    break
            
            print(f"  Completing task: {logical_id} ({task_id})")
            
            self.start_task(task_id)
            self.complete_task(task_id, f"Task {logical_id} completed")
            completed_tasks.append(logical_id)
            
            step += 1
            
            # Safety check to avoid infinite loops
            if step > 20:
                break
        
        print(f"Completed tasks in order: {completed_tasks}")
        
        # Verify all tasks were completed
        expected_tasks = ['database', 'config', 'logging', 'auth_db', 'metrics', 
                         'auth_service', 'auth_api', 'integration']
        
        for task in expected_tasks:
            assert task in completed_tasks, f"Task {task} was not completed"
        
        # Verify dependency order constraints
        def get_completion_order(task_name):
            return completed_tasks.index(task_name)
        
        # Database must come before auth_db
        assert get_completion_order('database') < get_completion_order('auth_db')
        
        # Config must come before logging
        assert get_completion_order('config') < get_completion_order('logging')
        
        # Database and logging must come before metrics
        assert get_completion_order('database') < get_completion_order('metrics')
        assert get_completion_order('logging') < get_completion_order('metrics')
        
        # Auth service depends on auth_db and logging
        assert get_completion_order('auth_db') < get_completion_order('auth_service')
        assert get_completion_order('logging') < get_completion_order('auth_service')
        
        # Auth API depends on auth_service and metrics
        assert get_completion_order('auth_service') < get_completion_order('auth_api')
        assert get_completion_order('metrics') < get_completion_order('auth_api')
        
        # Integration depends on auth_api
        assert get_completion_order('auth_api') < get_completion_order('integration')

    @pytest.mark.asyncio
    async def test_agent_simulation_full_workflow(self):
        """Simulate a complete autonomous agent workflow"""
        markdown = """
# Issues Structure
- [mvp] MVP Development, t=Epic, p=0
    - [backend] Backend Development, t=Feature, p=0
        - [models] Data Models, t=Task, p=0
        - [api] API Implementation, t=Task, p=1, deps=[models]
        - [auth] Authentication, t=Task, p=2, deps=[api]
    - [frontend] Frontend Development, t=Feature, p=1
        - [components] UI Components, t=Task, p=0
        - [pages] Application Pages, t=Task, p=1, deps=[components]
        - [integration] Frontend Integration, t=Task, p=2, deps=[pages,auth]
    - [deployment] Deployment, t=Feature, p=2
        - [config] Deploy Configuration, t=Task, p=0
        - [pipeline] CI/CD Pipeline, t=Task, p=1, deps=[config]
        - [release] Production Release, t=Task, p=2, deps=[pipeline,integration]

# Detailed Content
## mvp
### description
Complete MVP with backend, frontend, and deployment pipeline.

### acceptance_criteria
- [ ] Backend API functional
- [ ] Frontend application deployed
- [ ] CI/CD pipeline operational
"""
        
        mapping = await self.import_markdown_issues(markdown)
        
        print(f"\n=== Test: Agent Simulation Full Workflow ===")
        print(f"Starting autonomous agent simulation...")
        
        agent_name = "autonomous_agent_v1"
        completed_count = 0
        polling_round = 1
        
        while True:
            print(f"\n--- Polling Round {polling_round} ---")
            
            # Agent polls for ready work
            ready_tasks = self.get_ready_tasks()
            
            if not ready_tasks:
                print("✅ No more tasks available. Agent workflow complete!")
                break
            
            print(f"Agent found {len(ready_tasks)} ready tasks:")
            for i, task in enumerate(ready_tasks):
                # Find logical ID
                logical_id = None
                for logical, physical in mapping.items():
                    if physical == task.id:
                        logical_id = logical
                        break
                print(f"  {i+1}. {logical_id} ({task.title}) - Priority: {task.priority}")
            
            # Agent selects highest priority task (first in list)
            selected_task = ready_tasks[0]
            selected_logical_id = None
            for logical, physical in mapping.items():
                if physical == selected_task.id:
                    selected_logical_id = logical
                    break
            
            print(f"🤖 Agent selected: {selected_logical_id}")
            
            # Agent starts working on the task
            self.start_task(selected_task.id, agent_name)
            print(f"🔄 Agent started working on {selected_logical_id}")
            
            # Simulate work completion
            completion_reason = f"Completed by {agent_name} - {selected_task.title}"
            self.complete_task(selected_task.id, completion_reason, agent_name)
            completed_count += 1
            
            print(f"✅ Agent completed {selected_logical_id} (Task #{completed_count})")
            
            polling_round += 1
            
            # Safety check
            if polling_round > 50:
                print("⚠️ Maximum polling rounds reached")
                break
        
        print(f"\n🎉 Agent simulation complete! Completed {completed_count} tasks in {polling_round-1} polling rounds.")
        
        # Verify all leaf tasks were completed
        leaf_tasks = ['models', 'api', 'auth', 'components', 'pages', 'integration', 
                     'config', 'pipeline', 'release']
        
        for logical_id in leaf_tasks:
            physical_id = mapping[logical_id]
            status = self.get_issue_status(physical_id)
            assert status == Status.CLOSED, f"Task {logical_id} should be closed but is {status}"
        
        print("✅ All leaf tasks successfully completed by autonomous agent!")

    @pytest.mark.asyncio 
    async def test_agent_error_handling(self):
        """Test agent behavior with blocked tasks and error conditions"""
        markdown = """
# Issues Structure
- [task1] Independent Task, t=Task, p=0
- [task2] Blocked Task, t=Task, p=1, deps=[missing_task]
- [task3] Another Independent Task, t=Task, p=2
"""
        
        # This should fail due to missing dependency
        parser = MarkdownParser()
        result = parser.parse(markdown)
        
        print(f"\n=== Test: Agent Error Handling ===")
        print(f"Parser errors: {result.errors}")
        
        # Should have validation errors due to missing dependency
        assert not result.is_valid
        assert any("depends on unknown issue 'missing_task'" in error for error in result.errors)

if __name__ == "__main__":
    # Run tests individually for debugging
    test_instance = TestLetsContinueProtocol()
    test_instance.setup_method()
    
    import asyncio
    asyncio.run(test_instance.test_simple_sequential_workflow())