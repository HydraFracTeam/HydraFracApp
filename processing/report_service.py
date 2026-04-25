from datetime import datetime
from typing import Dict, List

class ProcessingReportService:
    def __init__(self):
        self.metrics_history: List[Dict] = []
    
    def add_metrics(self, operation: str, metrics: Dict):
        """Добавляет метрики операции в историю"""
        self.metrics_history.append({
            'timestamp': datetime.now(),
            'operation': operation,
            'metrics': metrics
        })
    
    def generate_report(self) -> str:
        """Формирует текстовый отчет"""
        report_lines = []
        
        for entry in self.metrics_history:
            timestamp = entry['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
            operation = entry['operation']
            metrics = entry['metrics']
            
            report_lines.append(f"{timestamp}: {operation}")
            
            for key, value in metrics.items():
                if key not in ['operation', 'timestamp']:
                    report_lines.append(f"  {key}: {value}")
            
            report_lines.append("")  # пустая строка между операциями
        
        return "\n".join(report_lines)
    
    def get_last_operation_metrics(self) -> Dict:
        """Возвращает метрики последней операции"""
        if self.metrics_history:
            return self.metrics_history[-1]['metrics']
        return {}
