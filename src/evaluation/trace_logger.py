"""Process trace logging for fidelity assessment."""
from datetime import datetime
from ..schema import log_event, Event

class TraceLogger:
    def __init__(self, conn):
        self.conn = conn
    
    def log_trace(self, cycle: int, component: str, action: str,
                  input_state: dict = None, output_state: dict = None, score: float = None):
        import json
        now = datetime.utcnow().isoformat()
        self.conn.execute(
            """INSERT INTO traces (cycle, component, action, input_state, output_state, score, timestamp)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (cycle, component, action,
             json.dumps(input_state) if input_state else None,
             json.dumps(output_state) if output_state else None,
             score, now)
        )
        self.conn.commit()
    
    def get_trace(self, cycle: int = None, component: str = None):
        query = "SELECT * FROM traces WHERE 1=1"
        params = []
        if cycle is not None:
            query += " AND cycle = ?"
            params.append(cycle)
        if component:
            query += " AND component = ?"
            params.append(component)
        query += " ORDER BY id"
        return self.conn.execute(query, params).fetchall()
    
    def export_trace(self, filepath: str):
        import json
        traces = self.conn.execute("SELECT * FROM traces ORDER BY id").fetchall()
        with open(filepath, 'w') as f:
            for t in traces:
                f.write(json.dumps(dict(t)) + "\n")
