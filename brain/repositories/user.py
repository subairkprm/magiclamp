"""
UserRepository - Repository pattern for User entity operations.
Provides clean interface between database and API for user-related queries.
"""
from typing import Optional, List
from core.database import DatabaseClient, QueryResult
from core.models import User
from core.exceptions import RecordNotFoundError, DatabaseError, DuplicateRecordError
from core.logger import get_logger

log = get_logger("repositories.user")


class UserRepository:
    """Repository for User entity operations with multi-tenant support."""

    def __init__(self, db_client: DatabaseClient):
        """
        Initialize UserRepository with a DatabaseClient.

        Args:
            db_client: DatabaseClient instance for database operations
        """
        self.db = db_client
        self.table = "users"

    def get_by_email(self, email: str, tenant_id: str) -> Optional[User]:
        """
        Get a user by email address within a tenant.

        Args:
            email: User's email address
            tenant_id: Tenant identifier for data isolation

        Returns:
            User model if found, None otherwise

        Raises:
            DatabaseError: If database query fails
        """
        try:
            result: QueryResult = self.db.select(
                table=self.table,
                columns="*",
                tenant_id=tenant_id,
                filters={"email": email},
                limit=1
            )

            if not result.success:
                raise DatabaseError(f"Failed to query user by email: {result.error}")

            if result.data:
                return User(**result.data[0])
            return None

        except Exception as e:
            log.error(f"Error getting user by email {email}: {str(e)}")
            if isinstance(e, DatabaseError):
                raise
            raise DatabaseError(f"Error retrieving user by email: {str(e)}")

    def get_by_id(self, user_id: str, tenant_id: str) -> User:
        """
        Get a user by ID within a tenant.

        Args:
            user_id: User's unique identifier
            tenant_id: Tenant identifier for data isolation

        Returns:
            User model

        Raises:
            RecordNotFoundError: If user not found
            DatabaseError: If database query fails
        """
        try:
            result: QueryResult = self.db.select(
                table=self.table,
                columns="*",
                tenant_id=tenant_id,
                filters={"id": user_id},
                limit=1
            )

            if not result.success:
                raise DatabaseError(f"Failed to query user by id: {result.error}")

            if not result.data:
                raise RecordNotFoundError(resource="User", identifier=user_id)

            return User(**result.data[0])

        except RecordNotFoundError:
            raise
        except Exception as e:
            log.error(f"Error getting user by id {user_id}: {str(e)}")
            if isinstance(e, DatabaseError):
                raise
            raise DatabaseError(f"Error retrieving user by id: {str(e)}")

    def create_user(
        self,
        name: str,
        email: str,
        password_hash: str,
        tenant_id: str,
        role: str = "user",
        is_active: bool = True
    ) -> User:
        """
        Create a new user within a tenant.

        Args:
            name: User's display name
            email: User's email address
            password_hash: Hashed password
            tenant_id: Tenant identifier for data isolation
            role: User role (default: "user")
            is_active: Whether user is active (default: True)

        Returns:
            Created User model

        Raises:
            DuplicateRecordError: If user with email already exists
            DatabaseError: If database operation fails
        """
        try:
            # Check if user already exists
            existing = self.get_by_email(email=email, tenant_id=tenant_id)
            if existing:
                raise DuplicateRecordError(
                    resource="User",
                    field="email",
                    value=email
                )

            # Create user data
            user_data = {
                "name": name,
                "email": email,
                "password_hash": password_hash,
                "role": role,
                "is_active": is_active,
            }

            # Insert into database
            result: QueryResult = self.db.insert(
                table=self.table,
                data=user_data,
                tenant_id=tenant_id
            )

            if not result.success:
                raise DatabaseError(f"Failed to create user: {result.error}")

            if not result.data:
                raise DatabaseError("User created but no data returned")

            log.info(f"Created user {email} in tenant {tenant_id}")
            return User(**result.data[0])

        except (DuplicateRecordError, DatabaseError):
            raise
        except Exception as e:
            log.error(f"Error creating user {email}: {str(e)}")
            raise DatabaseError(f"Error creating user: {str(e)}")

    def get_all(self, tenant_id: str, limit: Optional[int] = None) -> List[User]:
        """
        Get all users within a tenant.

        Args:
            tenant_id: Tenant identifier for data isolation
            limit: Maximum number of users to return (optional)

        Returns:
            List of User models

        Raises:
            DatabaseError: If database query fails
        """
        try:
            result: QueryResult = self.db.select(
                table=self.table,
                columns="*",
                tenant_id=tenant_id,
                order_by="created_at.desc",
                limit=limit
            )

            if not result.success:
                raise DatabaseError(f"Failed to query users: {result.error}")

            return [User(**user_data) for user_data in result.data]

        except Exception as e:
            log.error(f"Error getting all users: {str(e)}")
            if isinstance(e, DatabaseError):
                raise
            raise DatabaseError(f"Error retrieving users: {str(e)}")

    def update_last_login(self, user_id: str, tenant_id: str) -> User:
        """
        Update the last login timestamp for a user.

        Args:
            user_id: User's unique identifier
            tenant_id: Tenant identifier for data isolation

        Returns:
            Updated User model

        Raises:
            DatabaseError: If database operation fails
        """
        try:
            from datetime import datetime

            result: QueryResult = self.db.update(
                table=self.table,
                data={"last_login": datetime.utcnow().isoformat()},
                tenant_id=tenant_id,
                filters={"id": user_id}
            )

            if not result.success:
                raise DatabaseError(f"Failed to update last login: {result.error}")

            if not result.data:
                raise RecordNotFoundError(resource="User", identifier=user_id)

            return User(**result.data[0])

        except Exception as e:
            log.error(f"Error updating last login for user {user_id}: {str(e)}")
            if isinstance(e, (DatabaseError, RecordNotFoundError)):
                raise
            raise DatabaseError(f"Error updating last login: {str(e)}")

    def delete(self, user_id: str, tenant_id: str) -> bool:
        """
        Delete a user from a tenant.

        Args:
            user_id: User's unique identifier
            tenant_id: Tenant identifier for data isolation

        Returns:
            True if user was deleted

        Raises:
            DatabaseError: If database operation fails
        """
        try:
            result: QueryResult = self.db.delete(
                table=self.table,
                tenant_id=tenant_id,
                filters={"id": user_id}
            )

            if not result.success:
                raise DatabaseError(f"Failed to delete user: {result.error}")

            log.info(f"Deleted user {user_id} from tenant {tenant_id}")
            return True

        except Exception as e:
            log.error(f"Error deleting user {user_id}: {str(e)}")
            if isinstance(e, DatabaseError):
                raise
            raise DatabaseError(f"Error deleting user: {str(e)}")
