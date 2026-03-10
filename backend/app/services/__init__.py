# Services

from typing import Type, TypeVar, Generic, Optional, Any
from sqlalchemy.orm import Session, Query
from sqlalchemy.exc import NoResultFound
from fastapi import HTTPException, status
from app.models.user import User

T = TypeVar('T')


class BaseService(Generic[T]):
    """
    Base service class providing common patterns for service layer operations.
    
    Provides reusable methods for:
    - get_or_404: Fetch record or raise 404
    - paginate_query: Add pagination to SQLAlchemy queries
    - apply_owner_filter: Filter by user ownership
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_or_404(self, model: Type[T], record_id: Any, user_id: Optional[str] = None) -> T:
        """
        Get a record by ID or raise 404.
        
        Args:
            model: SQLAlchemy model class
            record_id: The ID to look up
            user_id: Optional user ID for ownership check
            
        Returns:
            The model instance
            
        Raises:
            HTTPException: 404 if record not found or not owned by user
        """
        query = self.db.query(model).filter(model.id == record_id)
        
        if user_id and hasattr(model, 'user_id'):
            query = query.filter(model.user_id == user_id)
            
        try:
            return query.one()
        except NoResultFound:
            if user_id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"{model.__name__} not found or access denied"
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"{model.__name__} not found"
                )
    
    def paginate_query(
        self,
        query: Query,
        page: int = 1,
        per_page: int = 20,
        max_per_page: int = 100
    ) -> dict:
        """
        Add pagination to a SQLAlchemy query.
        
        Args:
            query: SQLAlchemy query object
            page: Current page number (1-based)
            per_page: Items per page
            max_per_page: Maximum allowed items per page
            
        Returns:
            Dict with paginated results and metadata
        """
        if page < 1:
            page = 1
        if per_page < 1:
            per_page = 20
        if per_page > max_per_page:
            per_page = max_per_page
            
        offset = (page - 1) * per_page
        
        # Get total count
        total = query.count()
        
        # Get paginated results
        items = query.offset(offset).limit(per_page).all()
        
        # Calculate pagination metadata
        total_pages = (total + per_page - 1) // per_page
        has_next = page < total_pages
        has_prev = page > 1
        
        return {
            'items': items,
            'total': total,
            'page': page,
            'per_page': per_page,
            'total_pages': total_pages,
            'has_next': has_next,
            'has_prev': has_prev
        }
    
    def apply_owner_filter(self, query: Query, model: Type[T], current_user: User) -> Query:
        """
        Apply user ownership filter to a query.
        
        Args:
            query: SQLAlchemy query object
            model: SQLAlchemy model class
            current_user: Current authenticated user
            
        Returns:
            Filtered query with ownership check
        """
        if hasattr(model, 'user_id'):
            return query.filter(model.user_id == str(current_user.id))
        elif hasattr(model, 'owner_id'):
            return query.filter(model.owner_id == str(current_user.id))
        else:
            # Model doesn't have ownership field, return original query
            return query
