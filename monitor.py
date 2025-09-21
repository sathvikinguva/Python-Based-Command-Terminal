"""
System monitoring functionality for PyTerm.
Provides CPU, memory, disk usage and process information.
"""

import time
from datetime import datetime
from typing import List, Dict, Any
import psutil
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn
from rich.panel import Panel
from rich.columns import Columns

from executor import SafeExecutor
from commands import Command


class MonitorCommand(Command):
    """System monitoring command."""
    
    def __init__(self, executor: SafeExecutor):
        super().__init__(executor)
        self.console = Console()
    
    def execute(self, args: List[str]) -> bool:
        """Execute the monitor command."""
        # Parse flags
        continuous = '-c' in args or '--continuous' in args
        processes = '-p' in args or '--processes' in args
        disk = '-d' in args or '--disk' in args
        network = '-n' in args or '--network' in args
        
        try:
            if continuous:
                self._continuous_monitor()
            else:
                self._single_snapshot(show_processes=processes, show_disk=disk, show_network=network)
            return True
        except KeyboardInterrupt:
            self.console.print("\n[yellow]Monitoring stopped[/yellow]")
            return True
        except Exception as e:
            self.console.print(f"[red]Error: {e}[/red]")
            return False
    
    def _single_snapshot(self, show_processes=True, show_disk=False, show_network=False):
        """Show a single system snapshot."""
        panels = []
        
        # System info panel
        sys_info = self._get_system_info()
        sys_table = Table(show_header=False, box=None)
        sys_table.add_column("Metric", style="cyan")
        sys_table.add_column("Value", style="green")
        
        for key, value in sys_info.items():
            sys_table.add_row(key, str(value))
        
        panels.append(Panel(sys_table, title="[bold blue]System Info[/bold blue]", border_style="blue"))
        
        # CPU and Memory panel
        cpu_mem_table = Table(show_header=False, box=None)
        cpu_mem_table.add_column("Resource", style="cyan")
        cpu_mem_table.add_column("Usage", style="green")
        cpu_mem_table.add_column("Details", style="dim")
        
        # CPU info
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()
        cpu_freq = psutil.cpu_freq()
        
        cpu_mem_table.add_row(
            "CPU", 
            f"{cpu_percent:.1f}%",
            f"{cpu_count} cores @ {cpu_freq.current:.0f}MHz" if cpu_freq else f"{cpu_count} cores"
        )
        
        # Memory info
        memory = psutil.virtual_memory()
        cpu_mem_table.add_row(
            "Memory",
            f"{memory.percent:.1f}%",
            f"{self._format_bytes(memory.used)} / {self._format_bytes(memory.total)}"
        )
        
        # Swap info
        swap = psutil.swap_memory()
        if swap.total > 0:
            cpu_mem_table.add_row(
                "Swap",
                f"{swap.percent:.1f}%",
                f"{self._format_bytes(swap.used)} / {self._format_bytes(swap.total)}"
            )
        
        panels.append(Panel(cpu_mem_table, title="[bold yellow]Resources[/bold yellow]", border_style="yellow"))
        
        # Show panels
        if len(panels) <= 2:
            self.console.print(Columns(panels, equal=True, expand=True))
        else:
            for panel in panels:
                self.console.print(panel)
        
        # Optional sections
        if show_disk:
            self._show_disk_usage()
        
        if show_network:
            self._show_network_info()
        
        if show_processes:
            self._show_top_processes()
    
    def _continuous_monitor(self):
        """Show continuous monitoring display."""
        self.console.print("[yellow]Continuous monitoring - Press Ctrl+C to stop[/yellow]")
        
        while True:
            # Clear screen
            self.console.clear()
            
            # Show timestamp
            self.console.print(f"[dim]Updated: {datetime.now().strftime('%H:%M:%S')}[/dim]")
            self.console.print()
            
            # Show system snapshot
            self._single_snapshot(show_processes=True)
            
            # Wait for next update
            time.sleep(self.executor.config.get('monitor_refresh_rate', 2.0))
    
    def _get_system_info(self) -> Dict[str, Any]:
        """Get basic system information."""
        boot_time = datetime.fromtimestamp(psutil.boot_time())
        uptime = datetime.now() - boot_time
        
        return {
            "System": psutil.os.name.title(),
            "Boot Time": boot_time.strftime('%Y-%m-%d %H:%M:%S'),
            "Uptime": self._format_timedelta(uptime),
            "Load Average": self._get_load_average(),
        }
    
    def _get_load_average(self) -> str:
        """Get system load average."""
        try:
            load_avg = psutil.getloadavg()
            return f"{load_avg[0]:.2f}, {load_avg[1]:.2f}, {load_avg[2]:.2f}"
        except AttributeError:
            # Not available on Windows
            return "N/A"
    
    def _show_disk_usage(self):
        """Show disk usage information."""
        self.console.print()
        
        disk_table = Table(title="[bold green]Disk Usage[/bold green]")
        disk_table.add_column("Device", style="cyan")
        disk_table.add_column("Mountpoint", style="blue")
        disk_table.add_column("Total", justify="right")
        disk_table.add_column("Used", justify="right")
        disk_table.add_column("Free", justify="right")
        disk_table.add_column("Usage", justify="right")
        
        for partition in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                disk_table.add_row(
                    partition.device,
                    partition.mountpoint,
                    self._format_bytes(usage.total),
                    self._format_bytes(usage.used),
                    self._format_bytes(usage.free),
                    f"{usage.percent:.1f}%"
                )
            except PermissionError:
                continue
        
        self.console.print(disk_table)
    
    def _show_network_info(self):
        """Show network interface information."""
        self.console.print()
        
        net_table = Table(title="[bold magenta]Network Interfaces[/bold magenta]")
        net_table.add_column("Interface", style="cyan")
        net_table.add_column("Bytes Sent", justify="right")
        net_table.add_column("Bytes Recv", justify="right")
        net_table.add_column("Packets Sent", justify="right")
        net_table.add_column("Packets Recv", justify="right")
        
        net_stats = psutil.net_io_counters(pernic=True)
        for interface, stats in net_stats.items():
            net_table.add_row(
                interface,
                self._format_bytes(stats.bytes_sent),
                self._format_bytes(stats.bytes_recv),
                str(stats.packets_sent),
                str(stats.packets_recv)
            )
        
        self.console.print(net_table)
    
    def _show_top_processes(self):
        """Show top processes by CPU usage."""
        self.console.print()
        
        max_processes = self.executor.config.get('max_processes_display', 10)
        
        proc_table = Table(title=f"[bold red]Top {max_processes} Processes[/bold red]")
        proc_table.add_column("PID", justify="right", style="cyan")
        proc_table.add_column("Name", style="blue")
        proc_table.add_column("CPU%", justify="right")
        proc_table.add_column("Memory%", justify="right")
        proc_table.add_column("Status", style="dim")
        
        try:
            # Get all processes with their info
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'status']):
                try:
                    processes.append(proc.info)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            # Sort by CPU usage
            processes.sort(key=lambda p: p['cpu_percent'] or 0, reverse=True)
            
            # Show top processes
            for proc in processes[:max_processes]:
                proc_table.add_row(
                    str(proc['pid']),
                    proc['name'][:20],  # Truncate long names
                    f"{proc['cpu_percent'] or 0:.1f}%",
                    f"{proc['memory_percent'] or 0:.1f}%",
                    proc['status']
                )
            
        except Exception as e:
            proc_table.add_row("Error", str(e), "", "", "")
        
        self.console.print(proc_table)
    
    def _format_bytes(self, bytes_val: int) -> str:
        """Format bytes in human-readable format."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_val < 1024.0:
                return f"{bytes_val:.1f} {unit}"
            bytes_val /= 1024.0
        return f"{bytes_val:.1f} PB"
    
    def _format_timedelta(self, td) -> str:
        """Format timedelta in human-readable format."""
        days = td.days
        hours, remainder = divmod(td.seconds, 3600)
        minutes, _ = divmod(remainder, 60)
        
        parts = []
        if days:
            parts.append(f"{days}d")
        if hours:
            parts.append(f"{hours}h")
        if minutes:
            parts.append(f"{minutes}m")
        
        return " ".join(parts) if parts else "< 1m"
    
    def help(self) -> str:
        return "monitor [-c|--continuous] [-p|--processes] [-d|--disk] [-n|--network] - Show system information"