"""
Data Analysis Engine for Phase 3
Production-grade data analysis with security controls and visualization
"""

import pandas as pd
import numpy as np
import io
import hashlib
from datetime import datetime, UTC
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import seaborn as sns
import base64

from backend.app.models.entities import Attachment, DataAnalysisJob
from backend.app.security.file_validator import FileValidator


class DataAnalyzer:
    """
    Production data analysis with:
    - Security controls (file size, row limits, memory limits)
    - Schema detection
    - Statistical analysis
    - Safe visualization generation
    - Export capabilities
    """
    
    # Security limits
    MAX_FILE_SIZE_MB = 50
    MAX_ROWS = 100000
    MAX_COLUMNS = 100
    MAX_MEMORY_MB = 500
    ALLOWED_FILE_TYPES = ['csv', 'xlsx', 'xls']
    
    def __init__(self, db: Session):
        self.db = db
        self.file_validator = FileValidator()
    
    async def analyze_file(
        self,
        file_id: str,
        operations: List[str],
        owner_id: str
    ) -> Dict[str, Any]:
        """
        Main analysis pipeline with security controls
        """
        # Step 1: Security validation
        file_record = self._validate_file_access(file_id, owner_id)
        if not file_record:
            raise ValueError("File not found or access denied")
        
        # Step 2: Load data with size limits
        df = self._load_data_safely(file_record)
        if df is None:
            raise ValueError("Failed to load data within security limits")
        
        # Step 3: Schema detection
        schema = self._detect_schema(df)
        
        # Step 4: Data quality assessment
        quality_assessment = self._assess_data_quality(df)
        
        # Step 5: Perform requested operations
        analysis_results = {}
        charts = []
        
        for operation in operations:
            try:
                result = self._perform_operation(df, operation, schema)
                analysis_results[operation] = result
                
                # Generate charts if applicable
                if operation in ['correlation', 'distribution', 'trend']:
                    chart_result = self._generate_chart(df, operation, schema)
                    if chart_result:
                        charts.append(chart_result)
                        
            except Exception as e:
                analysis_results[operation] = {"error": str(e)}
        
        # Step 6: Calculate statistics
        statistics = self._calculate_statistics(df, schema)
        
        return {
            "file_name": file_record.filename,
            "file_type": file_record.file_type,
            "row_count": len(df),
            "column_count": len(df.columns),
            "schema": schema,
            "statistics": statistics,
            "quality_assessment": quality_assessment,
            "analysis_results": analysis_results,
            "charts": charts,
            "data_quality_score": quality_assessment.get("overall_score", 0.0),
            "missing_values": quality_assessment.get("missing_values", {})
        }
    
    def _validate_file_access(self, file_id: str, owner_id: str) -> Optional[Attachment]:
        """Validate file access with ownership check"""
        file_record = self.db.query(Attachment).filter(Attachment.id == file_id).first()
        
        if not file_record:
            return None
        
        # Security: users can only analyze their own files
        if file_record.user_id != owner_id:
            return None
        
        # Check file type
        file_ext = file_record.filename.split('.')[-1].lower()
        if file_ext not in self.ALLOWED_FILE_TYPES:
            raise ValueError(f"File type {file_ext} not allowed")
        
        # Check file size
        if file_record.size > self.MAX_FILE_SIZE_MB * 1024 * 1024:
            raise ValueError(f"File size exceeds limit of {self.MAX_FILE_SIZE_MB}MB")
        
        return file_record
    
    def _load_data_safely(self, file_record: Attachment) -> Optional[pd.DataFrame]:
        """Load data with security limits"""
        try:
            # Read file content
            file_path = file_record.storage_path
            file_ext = file_record.filename.split('.')[-1].lower()
            
            # Load with row limit
            if file_ext == 'csv':
                df = pd.read_csv(file_path, nrows=self.MAX_ROWS)
            elif file_ext in ['xlsx', 'xls']:
                df = pd.read_excel(file_path, nrows=self.MAX_ROWS)
            else:
                return None
            
            # Check column limit
            if len(df.columns) > self.MAX_COLUMNS:
                df = df.iloc[:, :self.MAX_COLUMNS]
            
            # Check memory usage
            memory_mb = df.memory_usage(deep=True).sum() / (1024 * 1024)
            if memory_mb > self.MAX_MEMORY_MB:
                raise ValueError(f"Data requires {memory_mb:.2f}MB, exceeds limit of {self.MAX_MEMORY_MB}MB")
            
            return df
            
        except Exception as e:
            print(f"Error loading data: {e}")
            return None
    
    def _detect_schema(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Detect schema information"""
        schema = {}
        
        for column in df.columns:
            col_type = str(df[column].dtype)
            
            # Detailed type classification
            if df[column].dtype == 'object':
                # Check if it's actually numeric
                try:
                    pd.to_numeric(df[column], errors='raise')
                    col_type = 'numeric'
                except:
                    # Check if it's datetime
                    try:
                        pd.to_datetime(df[column], errors='raise')
                        col_type = 'datetime'
                    except:
                        col_type = 'text'
            
            schema[column] = {
                "type": col_type,
                "nullable": df[column].isnull().any(),
                "unique_values": df[column].nunique(),
                "sample_values": df[column].head(3).tolist()
            }
        
        return schema
    
    def _assess_data_quality(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Assess data quality"""
        missing_values = {}
        total_cells = len(df) * len(df.columns)
        missing_cells = 0
        
        for column in df.columns:
            missing_count = df[column].isnull().sum()
            missing_pct = (missing_count / len(df)) * 100
            missing_values[column] = {
                "count": int(missing_count),
                "percentage": round(missing_pct, 2)
            }
            missing_cells += missing_count
        
        # Calculate overall quality score
        quality_score = 1.0 - (missing_cells / total_cells)
        
        # Check for duplicates
        duplicate_rows = df.duplicated().sum()
        duplicate_penalty = (duplicate_rows / len(df)) * 0.1
        quality_score -= duplicate_penalty
        
        return {
            "missing_values": missing_values,
            "overall_score": round(max(0.0, quality_score), 2),
            "duplicate_rows": int(duplicate_rows),
            "total_cells": total_cells,
            "missing_cells": int(missing_cells)
        }
    
    def _perform_operation(
        self,
        df: pd.DataFrame,
        operation: str,
        schema: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Perform specific analysis operation"""
        
        if operation == "filter":
            return self._filter_data(df, schema)
        elif operation == "sort":
            return self._sort_data(df, schema)
        elif operation == "group":
            return self._group_data(df, schema)
        elif operation == "aggregate":
            return self._aggregate_data(df, schema)
        elif operation == "correlation":
            return self._calculate_correlation(df, schema)
        elif operation == "distribution":
            return self._analyze_distribution(df, schema)
        elif operation == "trend":
            return self._analyze_trend(df, schema)
        else:
            return {"error": f"Unknown operation: {operation}"}
    
    def _filter_data(self, df: pd.DataFrame, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Filter data (placeholder - would need user parameters)"""
        # In production, this would accept filter criteria
        return {
            "message": "Filter operation requires specific criteria",
            "available_columns": list(df.columns),
            "sample": df.head(5).to_dict()
        }
    
    def _sort_data(self, df: pd.DataFrame, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Sort data by first numeric column"""
        numeric_cols = [col for col, info in schema.items() if 'numeric' in info['type'].lower()]
        
        if numeric_cols:
            sorted_df = df.sort_values(numeric_cols[0])
            return {
                "sorted_by": numeric_cols[0],
                "sample": sorted_df.head(5).to_dict()
            }
        else:
            return {"error": "No numeric columns found for sorting"}
    
    def _group_data(self, df: pd.DataFrame, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Group data by first categorical column"""
        categorical_cols = [col for col, info in schema.items() if 'text' in info['type'].lower()]
        
        if categorical_cols:
            grouped = df.groupby(categorical_cols[0]).size().to_dict()
            return {
                "grouped_by": categorical_cols[0],
                "group_counts": grouped
            }
        else:
            return {"error": "No categorical columns found for grouping"}
    
    def _aggregate_data(self, df: pd.DataFrame, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate aggregations for numeric columns"""
        numeric_cols = [col for col, info in schema.items() if 'numeric' in info['type'].lower()]
        
        if numeric_cols:
            aggregations = df[numeric_cols].agg(['mean', 'median', 'std', 'min', 'max']).to_dict()
            return {
                "aggregations": aggregations,
                "numeric_columns": numeric_cols
            }
        else:
            return {"error": "No numeric columns found for aggregation"}
    
    def _calculate_correlation(self, df: pd.DataFrame, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate correlation matrix for numeric columns"""
        numeric_cols = [col for col, info in schema.items() if 'numeric' in info['type'].lower()]
        
        if len(numeric_cols) >= 2:
            correlation_matrix = df[numeric_cols].corr().to_dict()
            return {
                "correlation_matrix": correlation_matrix,
                "numeric_columns": numeric_cols
            }
        else:
            return {"error": "Need at least 2 numeric columns for correlation"}
    
    def _analyze_distribution(self, df: pd.DataFrame, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze distribution of numeric columns"""
        numeric_cols = [col for col, info in schema.items() if 'numeric' in info['type'].lower()]
        
        if numeric_cols:
            distributions = {}
            for col in numeric_cols[:5]:  # Limit to first 5 numeric columns
                distributions[col] = {
                    "mean": float(df[col].mean()),
                    "median": float(df[col].median()),
                    "std": float(df[col].std()),
                    "min": float(df[col].min()),
                    "max": float(df[col].max()),
                    "quartiles": {
                        "25%": float(df[col].quantile(0.25)),
                        "50%": float(df[col].quantile(0.50)),
                        "75%": float(df[col].quantile(0.75))
                    }
                }
            return {"distributions": distributions}
        else:
            return {"error": "No numeric columns found for distribution analysis"}
    
    def _analyze_trend(self, df: pd.DataFrame, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze trends (requires datetime column)"""
        datetime_cols = [col for col, info in schema.items() if 'datetime' in info['type'].lower()]
        
        if datetime_cols:
            # Convert to datetime if needed
            df_copy = df.copy()
            for col in datetime_cols:
                df_copy[col] = pd.to_datetime(df_copy[col], errors='coerce')
            
            # Sort by datetime
            df_copy = df_copy.sort_values(datetime_cols[0])
            
            return {
                "datetime_column": datetime_cols[0],
                "date_range": {
                    "start": str(df_copy[datetime_cols[0]].min()),
                    "end": str(df_copy[datetime_cols[0]].max())
                },
                "sample": df_copy.head(5).to_dict()
            }
        else:
            return {"error": "No datetime columns found for trend analysis"}
    
    def _calculate_statistics(self, df: pd.DataFrame, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate comprehensive statistics"""
        statistics = {
            "overview": {
                "rows": len(df),
                "columns": len(df.columns),
                "memory_usage_mb": round(df.memory_usage(deep=True).sum() / (1024 * 1024), 2)
            },
            "column_stats": {}
        }
        
        for column in df.columns:
            col_stats = {
                "dtype": str(df[column].dtype),
                "non_null_count": int(df[column].count()),
                "null_count": int(df[column].isnull().sum())
            }
            
            # Add numeric statistics if applicable
            if pd.api.types.is_numeric_dtype(df[column]):
                col_stats.update({
                    "mean": float(df[column].mean()),
                    "std": float(df[column].std()),
                    "min": float(df[column].min()),
                    "max": float(df[column].max()),
                    "median": float(df[column].median())
                })
            
            statistics["column_stats"][column] = col_stats
        
        return statistics
    
    def _generate_chart(
        self,
        df: pd.DataFrame,
        chart_type: str,
        schema: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Generate chart safely and return as base64"""
        try:
            plt.figure(figsize=(10, 6))
            
            numeric_cols = [col for col, info in schema.items() if 'numeric' in info['type'].lower()]
            
            if chart_type == "correlation" and len(numeric_cols) >= 2:
                # Correlation heatmap
                corr_matrix = df[numeric_cols].corr()
                sns.heatmap(corr_matrix, annot=True, cmap='coolwarm', center=0)
                plt.title('Correlation Matrix')
                
            elif chart_type == "distribution" and numeric_cols:
                # Distribution plot for first numeric column
                df[numeric_cols[0]].hist(bins=30, edgecolor='black')
                plt.title(f'Distribution of {numeric_cols[0]}')
                plt.xlabel(numeric_cols[0])
                plt.ylabel('Frequency')
                
            elif chart_type == "trend" and numeric_cols:
                # Line plot for first numeric column
                plt.plot(df.index, df[numeric_cols[0]])
                plt.title(f'Trend of {numeric_cols[0]}')
                plt.xlabel('Index')
                plt.ylabel(numeric_cols[0])
            
            else:
                plt.close()
                return None
            
            # Convert to base64
            img_buffer = io.BytesIO()
            plt.savefig(img_buffer, format='png', dpi=100, bbox_inches='tight')
            img_buffer.seek(0)
            img_base64 = base64.b64encode(img_buffer.read()).decode()
            plt.close()
            
            return {
                "chart_type": chart_type,
                "image_base64": img_base64,
                "format": "png"
            }
            
        except Exception as e:
            print(f"Error generating chart: {e}")
            plt.close()
            return None
    
    def export_results(
        self,
        df: pd.DataFrame,
        analysis_results: Dict[str, Any],
        export_format: str = "csv"
    ) -> str:
        """Export analysis results to file"""
        try:
            timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
            
            if export_format == "csv":
                filename = f"analysis_results_{timestamp}.csv"
                filepath = f"./storage/exports/{filename}"
                df.to_csv(filepath, index=False)
                
            elif export_format == "xlsx":
                filename = f"analysis_results_{timestamp}.xlsx"
                filepath = f"./storage/exports/{filename}"
                
                with pd.ExcelWriter(filepath) as writer:
                    df.to_excel(writer, sheet_name='Data', index=False)
                    
                    # Add summary sheet
                    summary_data = []
                    for operation, result in analysis_results.items():
                        if isinstance(result, dict) and "error" not in result:
                            summary_data.append({
                                "Operation": operation,
                                "Status": "Success",
                                "Details": str(result)[:100]
                            })
                        else:
                            summary_data.append({
                                "Operation": operation,
                                "Status": "Failed",
                                "Details": str(result.get("error", "Unknown error"))[:100]
                            })
                    
                    pd.DataFrame(summary_data).to_excel(
                        writer, sheet_name='Summary', index=False
                    )
            
            return filepath
            
        except Exception as e:
            print(f"Error exporting results: {e}")
            return None