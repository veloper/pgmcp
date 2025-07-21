from typing import TYPE_CHECKING, Any, Callable, Dict, Generic, List, Literal, Optional, Type, TypeVar, Union, overload

from sqlalchemy import and_, asc, desc, distinct, func, or_, select, text
from sqlalchemy.orm import joinedload, selectinload, subqueryload
from sqlalchemy.sql.selectable import Select


if TYPE_CHECKING:
    from pgmcp.mixin.RailsQueryInterfaceMixin import RailsQueryInterfaceMixin

T = TypeVar("T", bound="RailsQueryInterfaceMixin")

class QueryBuilder(Generic[T]):
    def __init__(self, model: Type[T]):
        self.model = model
        self._stmt = select(model)
        self._distinct_value = False
        self._order_clauses: List[Any] = []  # Track order clauses for reverse_order
        self._custom_select_used = False  # Track if custom select is used

    # ==================================
    # Query Modifiers (Rails-like)
    # ==================================

    def where(self, *args, **kwargs) -> "QueryBuilder[T]":
        """Rails: Model.where(condition)"""
        if args and kwargs:
            # Combine args and kwargs with AND
            conditions = list(args)
            for key, value in kwargs.items():
                attr = getattr(self.model, key)
                conditions.append(attr == value)
            self._stmt = self._stmt.filter(and_(*conditions))
        elif args:
            self._stmt = self._stmt.filter(*args)
        elif kwargs:
            conditions = []
            for key, value in kwargs.items():
                attr = getattr(self.model, key)
                if isinstance(value, (list, tuple)):
                    conditions.append(attr.in_(value))
                elif value is None:
                    conditions.append(attr.is_(None))
                else:
                    conditions.append(attr == value)
            self._stmt = self._stmt.filter(and_(*conditions))
        return self

    def or_where(self, *args, **kwargs) -> "QueryBuilder[T]":
        """Rails: Model.where.or(condition) - but more explicit"""
        conditions = []
        if args:
            conditions.extend(args)
        if kwargs:
            for key, value in kwargs.items():
                attr = getattr(self.model, key)
                conditions.append(attr == value)
        
        if conditions:
            self._stmt = self._stmt.filter(or_(*conditions))
        return self

    def where_not(self, *args, **kwargs) -> "QueryBuilder[T]":
        """Rails: Model.where.not(condition)"""
        conditions = []
        if args:
            conditions.extend(args)
        if kwargs:
            for key, value in kwargs.items():
                attr = getattr(self.model, key)
                if isinstance(value, (list, tuple)):
                    conditions.append(~attr.in_(value))
                elif value is None:
                    conditions.append(attr.is_not(None))
                else:
                    conditions.append(attr != value)
        
        if conditions:
            self._stmt = self._stmt.filter(and_(*conditions))
        return self

    @overload
    def order(self, column: str) -> "QueryBuilder[T]": ...
    @overload
    def order(self, column: str, direction: Literal["asc", "desc"]) -> "QueryBuilder[T]": ...
    @overload
    def order(self, column: Any, direction: Literal["asc", "desc"]) -> "QueryBuilder[T]": ...
    @overload
    def order(self, column: Any) -> "QueryBuilder[T]": ...
    @overload
    def order(self, **kwargs: Literal["asc", "desc"]) -> "QueryBuilder[T]": ...
    def order(self, *args, **kwargs) -> "QueryBuilder[T]":
        """
        Rails: Model.order(:column) or Model.order(column: :desc)
        Pythonic: Model.order(column=desc) or Model.order(column=asc)
        Also supports: Model.order(column, "asc") or Model.order(column, "desc")
        """
        order_clauses = []
        
        # Handle positional arguments
        if len(args) == 1:
            # Single argument: column only
            col = args[0]
            if isinstance(col, str):
                order_clauses.append(self._resolve_column(col))
            else:
                order_clauses.append(col)
        elif len(args) == 2:
            # Two arguments: column and direction
            col, direction = args
            if isinstance(col, str):
                resolved_col = self._resolve_column(col)
            else:
                resolved_col = col
            
            if isinstance(direction, str) and direction in ("asc", "desc"):
                # Handle different column types safely
                try:
                    if direction == "asc":
                        order_clauses.append(resolved_col.asc())  # type: ignore
                    else:
                        order_clauses.append(resolved_col.desc())  # type: ignore
                except AttributeError:
                    # For text() objects, use asc() and desc() functions
                    order_clauses.append(asc(resolved_col) if direction == "asc" else desc(resolved_col))
            else:
                order_clauses.append(resolved_col)
        else:
            # Multiple arguments: treat as individual columns
            for col in args:
                if isinstance(col, str):
                    order_clauses.append(self._resolve_column(col))
                else:
                    order_clauses.append(col)
        
        # Handle keyword arguments
        for key, value in kwargs.items():
            attr = getattr(self.model, key)
            if callable(value):
                order_clauses.append(value(attr))
            elif isinstance(value, str) and value in ("asc", "desc"):
                order_clauses.append(attr.asc() if value == "asc" else attr.desc())
            else:
                order_clauses.append(attr == value)
        
        self._stmt = self._stmt.order_by(*order_clauses)
        self._order_clauses.extend(order_clauses)
        return self
    
    def reorder(self, *args) -> "QueryBuilder[T]":
        """Rails: Model.reorder() - clears existing order and applies new"""
        self._stmt = self._stmt.order_by(None).order_by(*args)
        self._order_clauses = list(args)  # Reset tracking
        return self

    def reverse_order(self) -> "QueryBuilder[T]":
        """Rails: Model.reverse_order"""
        if self._order_clauses:
            # Reverse the tracked order clauses
            reversed_orders = []
            for order_clause in self._order_clauses:
                # Check if it's already a desc() or asc() clause
                if hasattr(order_clause, 'desc'):
                    # It's a column, reverse it
                    reversed_orders.append(order_clause.desc())
                elif hasattr(order_clause, 'asc'):
                    # It's a column, reverse it  
                    reversed_orders.append(order_clause.asc())
                elif str(order_clause).upper().endswith(' DESC'):
                    # It's already DESC, make it ASC
                    # This is a simple heuristic for string-based order clauses
                    col_name = str(order_clause).replace(' DESC', '').replace(' desc', '')
                    col_attr = getattr(self.model, col_name) if hasattr(self.model, col_name) else order_clause
                    reversed_orders.append(asc(col_attr))
                elif str(order_clause).upper().endswith(' ASC'):
                    # It's already ASC, make it DESC
                    col_name = str(order_clause).replace(' ASC', '').replace(' asc', '')
                    col_attr = getattr(self.model, col_name) if hasattr(self.model, col_name) else order_clause
                    reversed_orders.append(desc(col_attr))
                else:
                    # Default column reference, make it DESC
                    reversed_orders.append(desc(order_clause))
            
            # Clear existing order and apply reversed order
            self._stmt = self._stmt.order_by(None).order_by(*reversed_orders)
            self._order_clauses = reversed_orders
        
        return self

    def limit(self, n: int) -> "QueryBuilder[T]":
        """Rails: Model.limit(n)"""
        self._stmt = self._stmt.limit(n)
        return self

    def offset(self, n: int) -> "QueryBuilder[T]":
        """Rails: Model.offset(n)"""
        self._stmt = self._stmt.offset(n)
        return self

    def distinct(self, *columns) -> "QueryBuilder[T]":
        """Rails: Model.distinct"""
        if columns:
            self._stmt = self._stmt.distinct(*columns)
        else:
            self._stmt = self._stmt.distinct()
            self._distinct_value = True
        return self

    def _resolve_column(self, col: str):
        """Resolve 'table.column' or 'column' to a SQLAlchemy column object."""
        if '.' in col:
            table, column = col.split('.', 1)
            # Try to find the model class for the table
            # Use the model's __table__ if it matches
            if hasattr(self.model, '__table__') and self.model.__table__.name == table:
                return self.model.__table__.columns[column]
            # Try joined tables (from relationships)
            for rel in getattr(self.model, '__mapper__').relationships:
                related = rel.mapper.class_
                if hasattr(related, '__table__') and related.__table__.name == table:
                    return related.__table__.columns[column]
            # Fallback: treat as raw SQL
            return text(col)
        else:
            return getattr(self.model, col)

    def select(self, *columns_or_expressions) -> "QueryBuilder[T]":
        """Rails: Model.select(*columns) or Model.select("custom sql")"""
        # Mark that we're using custom select
        self._custom_select_used = True
        self._aggregate_columns = []  # Store info about aggregate columns
        
        # Convert columns/expressions to proper format
        select_items = []
        for idx, item in enumerate(columns_or_expressions):
            if isinstance(item, str):
                # Handle table.* expansion
                if ".*" in item:
                    table_name = item.replace(".*", "")
                    # Check if this matches our model's table name
                    if hasattr(self.model, '__tablename__') and table_name == self.model.__tablename__:
                        # Expand to all model columns - use actual column objects
                        model_columns = [getattr(self.model.__table__.c, col.name) for col in self.model.__table__.columns]
                        select_items.extend(model_columns)
                    else:
                        # Keep as-is for other table expansions
                        select_items.append(text(item))
                else:
                    # Handle regular column resolution
                    resolved = self._resolve_column(item)
                    select_items.append(resolved)
                    
                    # Check if this looks like an aggregate (contains AS clause)
                    if " AS " in item:
                        alias = item.split(' AS ')[-1].strip()
                        self._aggregate_columns.append((alias, item))
            else:
                # Direct SQLAlchemy expressions
                select_items.append(item)
        
        # Apply the select to our statement while preserving joins and other clauses
        if hasattr(self._stmt, 'with_only_columns'):
            # Use with_only_columns to replace the selected columns
            try:
                self._stmt = self._stmt.with_only_columns(*select_items)
            except Exception as e:
                # Fallback - rebuild the statement from scratch to preserve joins
                base_stmt = select(*select_items).select_from(self._stmt.get_final_froms()[0])
                
                # Copy joins from the original statement
                for join in getattr(self._stmt, '_joins', []):
                    base_stmt = base_stmt.join(join.right, join.onclause, isouter=join.isouter)
                
                # Copy other clauses
                if hasattr(self._stmt, '_where_criteria') and self._stmt._where_criteria:
                    base_stmt = base_stmt.where(*self._stmt._where_criteria)
                if hasattr(self._stmt, '_group_by_clauses') and self._stmt._group_by_clauses:
                    base_stmt = base_stmt.group_by(*self._stmt._group_by_clauses)
                if hasattr(self._stmt, '_order_by_clauses') and self._stmt._order_by_clauses:
                    base_stmt = base_stmt.order_by(*self._stmt._order_by_clauses)
                if hasattr(self._stmt, '_limit_clause') and self._stmt._limit_clause is not None:
                    base_stmt = base_stmt.limit(self._stmt._limit_clause)
                if hasattr(self._stmt, '_offset_clause') and self._stmt._offset_clause is not None:
                    base_stmt = base_stmt.offset(self._stmt._offset_clause)
                    
                self._stmt = base_stmt
        else:
            # Fallback - create new select statement
            self._stmt = select(*select_items)
        return self

    def group(self, *columns) -> "QueryBuilder[T]":
        """Rails: Model.group(:column)"""
        group_columns = []
        for col in columns:
            if isinstance(col, str):
                group_columns.append(self._resolve_column(col))
            else:
                group_columns.append(col)
        self._stmt = self._stmt.group_by(*group_columns)
        return self

    def group_by(self, *columns) -> "QueryBuilder[T]":
        """Alias for group()"""
        return self.group(*columns)

    def having(self, *conditions) -> "QueryBuilder[T]":
        """Rails: Model.having(condition)"""
        processed_conditions = []
        for condition in conditions:
            if isinstance(condition, str):
                # Convert string conditions to text() objects for SQLAlchemy
                processed_conditions.append(text(condition))
            else:
                processed_conditions.append(condition)
        
        self._stmt = self._stmt.having(*processed_conditions)
        return self

    def joins(self, *relationships) -> "QueryBuilder[T]":
        """Rails: Model.joins(:association)"""
        for rel in relationships:
            if isinstance(rel, str):
                # Convert string to relationship attribute
                rel_attr = getattr(self.model, rel)
                self._stmt = self._stmt.join(rel_attr)
            else:
                self._stmt = self._stmt.join(rel)
        return self

    def left_joins(self, *relationships) -> "QueryBuilder[T]":
        """Rails: Model.left_joins(:association)"""
        for rel in relationships:
            if isinstance(rel, str):
                rel_attr = getattr(self.model, rel)
                self._stmt = self._stmt.outerjoin(rel_attr)
            else:
                self._stmt = self._stmt.outerjoin(rel)
        return self

    def includes(self, *relationships) -> "QueryBuilder[T]":
        """Rails: Model.includes(:association) - eager loading"""
        options = []
        for rel in relationships:
            if isinstance(rel, str):
                rel_attr = getattr(self.model, rel)
                options.append(joinedload(rel_attr))
            else:
                options.append(joinedload(rel))
        self._stmt = self._stmt.options(*options)
        return self

    def preload(self, *relationships) -> "QueryBuilder[T]":
        """Rails: Model.preload(:association) - separate queries"""
        options = []
        for rel in relationships:
            if isinstance(rel, str):
                rel_attr = getattr(self.model, rel)
                options.append(selectinload(rel_attr))
            else:
                options.append(selectinload(rel))
        self._stmt = self._stmt.options(*options)
        return self

    def eager_load(self, *relationships) -> "QueryBuilder[T]":
        """Rails: Model.eager_load(:association) - LEFT OUTER JOIN"""
        options = []
        for rel in relationships:
            if isinstance(rel, str):
                rel_attr = getattr(self.model, rel)
                options.append(subqueryload(rel_attr))
            else:
                options.append(subqueryload(rel))
        self._stmt = self._stmt.options(*options)
        return self

    def readonly(self) -> "QueryBuilder[T]":
        """Rails: Model.readonly"""
        # SQLAlchemy doesn't have direct readonly, but we can track this
        # and implement it in the session if needed
        return self

    def lock(self, mode: str = "UPDATE") -> "QueryBuilder[T]":
        """Rails: Model.lock"""
        self._stmt = self._stmt.with_for_update()
        return self

    def from_table(self, table_or_subquery) -> "QueryBuilder[T]":
        """Rails: Model.from(table)"""
        self._stmt = self._stmt.select_from(table_or_subquery)
        return self

    def none(self) -> "QueryBuilder[T]":
        """Rails: Model.none - returns empty relation"""
        self._stmt = self._stmt.filter(text("1=0"))
        return self

    def unscope(self, *scopes) -> "QueryBuilder[T]":
        """Rails: Model.unscope(:where, :order, etc.)"""
        # This would require tracking applied scopes
        # For now, return a fresh query builder
        return QueryBuilder(self.model)

    # ==================================
    # Execution Methods (Rails Finders)
    # ==================================

    def rehydrate_model_from_row(self, row_dict: Dict[str, Any]) -> T:
        """Rehydrate a model instance from raw row data, setting model fields directly and storing extras for dict access."""
        # Get model column names
        model_columns = {col.name for col in self.model.__table__.columns}
        
        # Extract model data (columns that exist in the model)
        model_data = {k: v for k, v in row_dict.items() if k in model_columns}
        
        # Extract extra data (aggregates, computed fields, etc.)
        extra_data = {k: v for k, v in row_dict.items() if k not in model_columns}
        
        # Create model instance with model data
        model_instance = self.model(**model_data)
        
        # Store extra data for dict-style access
        if extra_data:
            model_instance._row_data = row_dict  # type: ignore
        
        return model_instance

    async def all(self) -> List[T]:
        """Rails: Model.all"""
        async with self.model.async_session() as session:
            result = await session.execute(self._stmt)
            
            # Check if we have a custom select that includes model columns
            if hasattr(self, '_custom_select_used') and self._custom_select_used:
                rows = result.all()
                models = []
                
                for idx, row in enumerate(rows):
                    # Build complete row dictionary from all available data
                    row_dict = {}
                    
                    # Add mapping data (this gets model columns)
                    if hasattr(row, '_mapping'):
                        row_dict.update(dict(row._mapping))
                    
                    # Try to access row as tuple/sequence to get all columns
                    row_as_tuple = None
                    try:
                        row_as_tuple = tuple(row)
                    except Exception:
                        pass  # Skip if can't access this way
                    
                    # Try to get aggregate fields by accessing row by index
                    # This is needed because SQLAlchemy sometimes doesn't include computed columns in _mapping
                    if hasattr(self._stmt, 'selected_columns'):
                        selected_cols = list(self._stmt.selected_columns)
                        
                        # Get the actual column count from the row
                        row_length = len(row_as_tuple) if row_as_tuple is not None else len(row)
                        
                        # If we have more values in the row than in selected_columns, 
                        # we need to manually handle the extra aggregate columns
                        if row_length > len(selected_cols):
                            # Process the known columns first
                            for i, col in enumerate(selected_cols):
                                # Extract column name from the column expression
                                if hasattr(col, 'name'):
                                    col_name = col.name
                                elif hasattr(col, 'key'):
                                    col_name = col.key
                                else:
                                    # For expressions like "COUNT(...) AS log_count", extract the alias
                                    col_str = str(col)
                                    if ' AS ' in col_str:
                                        col_name = col_str.split(' AS ')[-1].strip()
                                    else:
                                        col_name = col_str.split('.')[-1].strip()
                                
                                # Add to row_dict if not already present
                                if col_name not in row_dict:
                                    try:
                                        value = row[i]
                                        row_dict[col_name] = value
                                    except (IndexError, KeyError):
                                        pass  # Skip if can't access this column
                            
                            # Now handle the extra columns that are likely aggregates
                            # We need to figure out what these are from the original select call
                            if hasattr(self, '_aggregate_columns'):
                                for i, (col_name, col_expr) in enumerate(self._aggregate_columns):
                                    actual_index = len(selected_cols) + i
                                    if actual_index < row_length:
                                        try:
                                            value = row[actual_index]
                                            row_dict[col_name] = value
                                        except (IndexError, KeyError):
                                            pass  # Skip if can't access this column
                        else:
                            # Normal processing when selected_columns matches row length
                            for i, col in enumerate(selected_cols):
                                # Extract column name from the column expression
                                if hasattr(col, 'name'):
                                    col_name = col.name
                                elif hasattr(col, 'key'):
                                    col_name = col.key
                                else:
                                    # For expressions like "COUNT(...) AS log_count", extract the alias
                                    col_str = str(col)
                                    if ' AS ' in col_str:
                                        col_name = col_str.split(' AS ')[-1].strip()
                                    else:
                                        col_name = col_str.split('.')[-1].strip()
                                
                                # Add to row_dict if not already present
                                if col_name not in row_dict:
                                    try:
                                        value = row[i]
                                        row_dict[col_name] = value
                                    except (IndexError, KeyError):
                                        pass  # Skip if can't access this column
                    
                    # Rehydrate the model instance
                    model_instance = self.rehydrate_model_from_row(row_dict)
                    models.append(model_instance)
                        
                return models
            else:
                # Normal query without custom select
                return list(result.scalars().all())

    async def first(self, n: Optional[int] = None) -> Union[Optional[T], List[T]]:
        """Rails: Model.first or Model.first(n)"""
        if n is not None:
            stmt = self._stmt.limit(n)
            async with self.model.async_session() as session:
                result = await session.execute(stmt)
                return list(result.scalars().all())
        else:
            async with self.model.async_session() as session:
                result = await session.execute(self._stmt)
                return result.scalars().first()

    async def last(self, n: Optional[int] = None) -> Union[Optional[T], List[T]]:
        """Rails: Model.last or Model.last(n)"""
        # Create a copy of the current builder and reverse its order
        reversed_builder = QueryBuilder(self.model)
        reversed_builder._stmt = self._stmt
        reversed_builder._order_clauses = self._order_clauses.copy()
        
        if self._order_clauses:
            # We have existing order, reverse it
            reversed_builder = reversed_builder.reverse_order()
        else:
            # No existing order, use default order by primary key desc
            reversed_builder = reversed_builder.order(desc(self.model.id))
        
        if n is not None:
            # Get n records and reverse them to maintain original order
            stmt = reversed_builder._stmt.limit(n)
            async with self.model.async_session() as session:
                result = await session.execute(stmt)
                records = list(result.scalars().all())
                return list(reversed(records))
        else:
            # Get the first record from the reversed query
            async with self.model.async_session() as session:
                result = await session.execute(reversed_builder._stmt)
                return result.scalars().first()

    async def find(self, *ids) -> Union[T, List[T]]:
        """Rails: Model.find(id) or Model.find([id1, id2])"""
        if len(ids) == 1:
            id_val = ids[0]
            if isinstance(id_val, (list, tuple)):
                # Multiple IDs passed as array
                stmt = select(self.model).filter(self.model.id.in_(id_val))
                async with self.model.async_session() as session:
                    result = await session.execute(stmt)
                    records = list(result.scalars().all())
                    if len(records) != len(id_val):
                        missing = set(id_val) - {r.id for r in records}
                        raise ValueError(f"Couldn't find {self.model.__name__} with ids: {missing}")
                    return records
            else:
                # Single ID
                stmt = select(self.model).filter(self.model.id == id_val)
                async with self.model.async_session() as session:
                    result = await session.execute(stmt)
                    record = result.scalars().first()
                    if record is None:
                        raise ValueError(f"Couldn't find {self.model.__name__} with id: {id_val}")
                    return record
        else:
            # Multiple IDs passed as separate arguments
            stmt = select(self.model).filter(self.model.id.in_(ids))
            async with self.model.async_session() as session:
                result = await session.execute(stmt)
                records = list(result.scalars().all())
                if len(records) != len(ids):
                    missing = set(ids) - {r.id for r in records}
                    raise ValueError(f"Couldn't find {self.model.__name__} with ids: {missing}")
                return records

    async def find_by(self, **kwargs) -> Optional[T]:
        """Rails: Model.find_by(attribute: value)"""
        builder = self.where(**kwargs)
        result = await builder.first()
        # Since we're calling first() without n parameter, it returns Optional[T]
        if isinstance(result, list):
            # This shouldn't happen when n is None, but handle it gracefully
            return result[0] if result else None
        return result

    async def find_by_or_raise(self, **kwargs) -> T:
        """Rails: Model.find_by!(attribute: value) - raises if not found"""
        record = await self.find_by(**kwargs)
        if record is None:
            raise ValueError(f"Couldn't find {self.model.__name__} with {kwargs}")
        return record

    async def take(self, n: Optional[int] = None) -> Union[Optional[T], List[T]]:
        """Rails: Model.take or Model.take(n) - no ordering"""
        if n is not None:
            stmt = select(self.model).limit(n)
            async with self.model.async_session() as session:
                result = await session.execute(stmt)
                return list(result.scalars().all())
        else:
            stmt = select(self.model).limit(1)
            async with self.model.async_session() as session:
                result = await session.execute(stmt)
                return result.scalars().first()

    async def exists(self, **kwargs) -> bool:
        """Rails: Model.exists?(conditions)"""
        if kwargs:
            builder = self.where(**kwargs)
            stmt = builder._stmt
        else:
            stmt = self._stmt
        
        exists_stmt = select(stmt.exists())
        async with self.model.async_session() as session:
            result = await session.execute(exists_stmt)
            return bool(result.scalar() or False)

    async def count(self, column: Optional[str] = None) -> int:
        """Rails: Model.count or Model.count(:column)"""
        if column:
            col_attr = getattr(self.model, column)
            count_stmt = self._stmt.with_only_columns(func.count(col_attr))
        else:
            count_stmt = self._stmt.with_only_columns(func.count())
        
        async with self.model.async_session() as session:
            result = await session.execute(count_stmt)
            return result.scalar_one()

    async def size(self) -> int:
        """Rails: Model.size - alias for count"""
        return await self.count()

    async def length(self) -> int:
        """Rails: Model.length - loads records and counts"""
        records = await self.all()
        return len(records)

    async def empty(self) -> bool:
        """Rails: Model.empty?"""
        return not await self.exists()

    async def any(self) -> bool:
        """Rails: Model.any?"""
        return await self.exists()

    async def many(self) -> bool:
        """Rails: Model.many? - more than one record"""
        count = await self.limit(2).count()
        return count > 1

    async def sum(self, column: str) -> Union[int, float]:
        """Rails: Model.sum(:column)"""
        col_attr = getattr(self.model, column)
        sum_stmt = self._stmt.with_only_columns(func.sum(col_attr))
        async with self.model.async_session() as session:
            result = await session.execute(sum_stmt)
            return result.scalar() or 0

    async def average(self, column: str) -> Optional[float]:
        """Rails: Model.average(:column)"""
        col_attr = getattr(self.model, column)
        avg_stmt = self._stmt.with_only_columns(func.avg(col_attr))
        async with self.model.async_session() as session:
            result = await session.execute(avg_stmt)
            return result.scalar()

    async def minimum(self, column: str) -> Any:
        """Rails: Model.minimum(:column)"""
        col_attr = getattr(self.model, column)
        min_stmt = self._stmt.with_only_columns(func.min(col_attr))
        async with self.model.async_session() as session:
            result = await session.execute(min_stmt)
            return result.scalar()

    async def maximum(self, column: str) -> Any:
        """Rails: Model.maximum(:column)"""
        col_attr = getattr(self.model, column)
        max_stmt = self._stmt.with_only_columns(func.max(col_attr))
        async with self.model.async_session() as session:
            result = await session.execute(max_stmt)
            return result.scalar()

    async def pluck(self, *columns) -> List[Any]:
        """Rails: Model.pluck(:column1, :column2)"""
        if not columns:
            raise ValueError("Must specify at least one column to pluck")
        
        col_attrs = []
        for col in columns:
            if isinstance(col, str):
                col_attrs.append(getattr(self.model, col))
            else:
                col_attrs.append(col)
        
        if len(col_attrs) == 1:
            stmt = self._stmt.with_only_columns(col_attrs[0])
            async with self.model.async_session() as session:
                result = await session.execute(stmt)
                return [row[0] for row in result.all()]
        else:
            stmt = self._stmt.with_only_columns(*col_attrs)
            async with self.model.async_session() as session:
                result = await session.execute(stmt)
                return [tuple(row) for row in result.all()]

    async def ids(self) -> List[Any]:
        """Rails: Model.ids - pluck primary key"""
        return await self.pluck('id')

    # ==================================
    # Batch Methods
    # ==================================

    async def find_each(self, batch_size: int = 1000, start: Optional[int] = None, 
                       finish: Optional[int] = None) -> List[T]:
        """Rails: Model.find_each"""
        stmt = self._stmt.order_by(self.model.id)
        
        if start is not None:
            stmt = stmt.filter(self.model.id >= start)
        if finish is not None:
            stmt = stmt.filter(self.model.id <= finish)
            
        stmt = stmt.limit(batch_size)
        
        async with self.model.async_session() as session:
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def find_in_batches(self, batch_size: int = 1000, start: Optional[int] = None,
                             finish: Optional[int] = None):
        """Rails: Model.find_in_batches - yields batches"""
        current_id = start or 0
        
        while True:
            stmt = self._stmt.order_by(self.model.id)
            stmt = stmt.filter(self.model.id > current_id)
            
            if finish is not None:
                stmt = stmt.filter(self.model.id <= finish)
                
            stmt = stmt.limit(batch_size)
            
            async with self.model.async_session() as session:
                result = await session.execute(stmt)
                batch = list(result.scalars().all())
                
                if not batch:
                    break
                    
                yield batch
                
                current_id = batch[-1].id
                
                if finish is not None and current_id >= finish:
                    break

    # ==================================
    # Utility Methods
    # ==================================

    def to_sql(self) -> str:
        """Rails: Model.to_sql - compile to SQL string"""
        return str(self._stmt.compile(compile_kwargs={"literal_binds": True}))

    def explain(self) -> str:
        """Rails: Model.explain - get query execution plan"""
        # This would need database-specific implementation
        return f"EXPLAIN {self.to_sql()}"

    def __repr__(self) -> str:
        return f"<QueryBuilder({self.model.__name__}) {self.to_sql()}>"
