"""
Utility functions for data manipulation and lookups.
"""
from typing import Any, Optional, Callable
import pandas as pd


class DataUtils:
    """Helper class providing Excel-like data lookup and aggregation functions."""
    
    @staticmethod
    def xlookup(
        lookup_value: Any,
        lookup_array: pd.Series,
        return_array: pd.Series,
        if_not_found: Any = None
    ) -> Any:
        """
        Excel-like XLOOKUP function. Searches for a value in lookup_array
        and returns the corresponding value from return_array.
        
        Args:
            lookup_value: The value to search for
            lookup_array: The array/series to search in
            return_array: The array/series to return value from
            if_not_found: Value to return if lookup_value not found (default: None)
            
        Returns:
            The corresponding value from return_array, or if_not_found if not found
        """
        if lookup_array.empty or return_array.empty:
            return if_not_found
        
        try:
            # Find matching indices
            mask = lookup_array == lookup_value
            if mask.any():
                # Get first match
                idx = mask.idxmax()
                return return_array.loc[idx]
        except Exception:
            pass
        
        return if_not_found
    
    @staticmethod
    def sumif(
        condition_array: pd.Series,
        condition_value: Any,
        sum_array: pd.Series
    ) -> float:
        """
        Excel-like SUMIF function. Sums values in sum_array where 
        condition_array matches condition_value.
        
        Args:
            condition_array: The array/series to check condition against
            sum_array: The array/series to sum
            condition_value: The value to match in condition_array
            
        Returns:
            Sum of matching values, or 0.0 if none found
        """
        try:
            mask = condition_array == condition_value
            if mask.any():
                return float(sum_array[mask].sum())
        except Exception:
            pass
        
        return 0.0
    
    @staticmethod
    def sumif_custom(
        condition_func: Callable[[pd.Series], pd.Series],
        sum_array: pd.Series
    ) -> float:
        """
        SUMIF with custom condition function.
        
        Args:
            condition_func: Function that returns boolean mask
            sum_array: The array/series to sum
            
        Returns:
            Sum of matching values
        """
        try:
            mask = condition_func(sum_array)
            if mask.any():
                return float(sum_array[mask].sum())
        except Exception:
            pass
        
        return 0.0
    
    @staticmethod
    def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
        """
        Safely divide two numbers, returning default if denominator is 0 or None.
        
        Args:
            numerator: Number to divide
            denominator: Number to divide by
            default: Value to return if division fails (default: 0.0)
            
        Returns:
            Result of division or default
        """
        try:
            if denominator is None or denominator == 0:
                return default
            return numerator / denominator
        except (TypeError, ZeroDivisionError):
            return default
    
    @staticmethod
    def coalesce(*args) -> Any:
        """
        Returns the first non-None value from arguments.
        Similar to SQL COALESCE.
        
        Args:
            *args: Values to check
            
        Returns:
            First non-None value, or None if all are None
        """
        for arg in args:
            if arg is not None and (not isinstance(arg, float) or not pd.isna(arg)):
                return arg
        return None

