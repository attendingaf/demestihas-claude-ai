#!/usr/bin/env python3
"""Interactive test interface for Pluma Local."""

import os
import sys
from datetime import datetime
from pluma_local import LocalPlumaAgent
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich import print as rprint

console = Console()

class PlumaTestInterface:
    """Interactive testing interface for Pluma Local."""
    
    def __init__(self):
        self.agent = LocalPlumaAgent()
        self.current_emails = []
        
    def run(self):
        """Run the interactive test interface."""
        console.clear()
        rprint(Panel.fit(
            "[bold cyan]Pluma Local Test Interface[/bold cyan]\n"
            "Test email drafting with Claude API",
            border_style="cyan"
        ))
        
        # Initialize Gmail
        if not self.agent.initialize():
            console.print("[red]❌ Failed to initialize Gmail service[/red]")
            console.print("Please run setup.py first to configure Gmail OAuth")
            return
        
        console.print("[green]✓ Gmail service initialized[/green]\n")
        
        while True:
            self.show_menu()
            choice = Prompt.ask(
                "\nSelect an option",
                choices=["1", "2", "3", "4", "5", "6", "q"],
                default="1"
            )
            
            if choice == "q":
                console.print("\n[yellow]Goodbye! 👋[/yellow]")
                break
            
            self.handle_choice(choice)
    
    def show_menu(self):
        """Display the main menu."""
        menu = Table(show_header=False, box=None)
        menu.add_column(style="cyan", width=3)
        menu.add_column(style="white")
        
        menu.add_row("1", "Fetch latest emails")
        menu.add_row("2", "Generate draft reply")
        menu.add_row("3", "Create Gmail draft")
        menu.add_row("4", "View email details")
        menu.add_row("5", "Show cache stats")
        menu.add_row("6", "Clear cache")
        menu.add_row("q", "Quit")
        
        console.print("\n[bold]Menu:[/bold]")
        console.print(menu)
    
    def handle_choice(self, choice: str):
        """Handle menu choice."""
        if choice == "1":
            self.fetch_emails()
        elif choice == "2":
            self.generate_draft()
        elif choice == "3":
            self.create_gmail_draft()
        elif choice == "4":
            self.view_email_details()
        elif choice == "5":
            self.show_stats()
        elif choice == "6":
            self.clear_cache()
    
    def fetch_emails(self):
        """Fetch and display latest emails."""
        console.print("\n[yellow]Fetching latest emails...[/yellow]")
        
        max_results = int(Prompt.ask("How many emails to fetch?", default="5"))
        self.current_emails = self.agent.fetch_latest_emails(max_results=max_results)
        
        if not self.current_emails:
            console.print("[red]No emails found[/red]")
            return
        
        # Display emails in a table
        table = Table(title=f"Latest {len(self.current_emails)} Emails")
        table.add_column("#", style="cyan", width=3)
        table.add_column("From", style="green", width=30)
        table.add_column("Subject", style="yellow")
        table.add_column("Date", style="magenta", width=20)
        
        for i, email in enumerate(self.current_emails, 1):
            from_addr = email['from'][:30] + "..." if len(email['from']) > 30 else email['from']
            subject = email['subject'][:40] + "..." if len(email['subject']) > 40 else email['subject']
            table.add_row(
                str(i),
                from_addr,
                subject,
                email['date'][:20]
            )
        
        console.print(table)
        console.print(f"\n[green]✓ Fetched {len(self.current_emails)} emails[/green]")
    
    def generate_draft(self):
        """Generate a draft reply for selected email."""
        if not self.current_emails:
            console.print("[red]No emails loaded. Please fetch emails first.[/red]")
            return
        
        # Select email
        email_num = int(Prompt.ask(
            f"Select email number (1-{len(self.current_emails)})",
            default="1"
        )) - 1
        
        if email_num < 0 or email_num >= len(self.current_emails):
            console.print("[red]Invalid email number[/red]")
            return
        
        email = self.current_emails[email_num]
        
        # Get optional instructions
        instructions = Prompt.ask(
            "Additional instructions (optional)",
            default=""
        )
        
        console.print("\n[yellow]Generating draft reply with Claude...[/yellow]")
        draft = self.agent.generate_draft_reply(email, instructions)
        
        # Display draft
        console.print(Panel(
            draft,
            title=f"Draft Reply to: {email['subject']}",
            border_style="green"
        ))
        
        # Store draft for later use
        email['draft'] = draft
        console.print("[green]✓ Draft generated and cached[/green]")
    
    def create_gmail_draft(self):
        """Create a Gmail draft from generated reply."""
        if not self.current_emails:
            console.print("[red]No emails loaded. Please fetch emails first.[/red]")
            return
        
        # Find emails with drafts
        emails_with_drafts = [
            (i, e) for i, e in enumerate(self.current_emails) 
            if 'draft' in e
        ]
        
        if not emails_with_drafts:
            console.print("[red]No drafts available. Please generate a draft first.[/red]")
            return
        
        # Select email with draft
        console.print("\n[bold]Emails with drafts:[/bold]")
        for idx, (i, email) in enumerate(emails_with_drafts, 1):
            console.print(f"{idx}. {email['subject']}")
        
        choice = int(Prompt.ask(
            f"Select draft (1-{len(emails_with_drafts)})",
            default="1"
        )) - 1
        
        if choice < 0 or choice >= len(emails_with_drafts):
            console.print("[red]Invalid choice[/red]")
            return
        
        email_idx, email = emails_with_drafts[choice]
        
        # Show draft and confirm
        console.print(Panel(
            email['draft'],
            title="Draft to be created",
            border_style="yellow"
        ))
        
        if Confirm.ask("Create this draft in Gmail?"):
            draft_id = self.agent.create_gmail_draft(email, email['draft'])
            if draft_id:
                console.print(f"[green]✓ Draft created in Gmail (ID: {draft_id})[/green]")
                console.print("[cyan]Check your Gmail drafts folder[/cyan]")
            else:
                console.print("[red]Failed to create Gmail draft[/red]")
    
    def view_email_details(self):
        """View full details of selected email."""
        if not self.current_emails:
            console.print("[red]No emails loaded. Please fetch emails first.[/red]")
            return
        
        email_num = int(Prompt.ask(
            f"Select email number (1-{len(self.current_emails)})",
            default="1"
        )) - 1
        
        if email_num < 0 or email_num >= len(self.current_emails):
            console.print("[red]Invalid email number[/red]")
            return
        
        email = self.current_emails[email_num]
        
        # Display full email details
        console.print(Panel.fit(
            f"[bold]From:[/bold] {email['from']}\n"
            f"[bold]To:[/bold] {email['to']}\n"
            f"[bold]Subject:[/bold] {email['subject']}\n"
            f"[bold]Date:[/bold] {email['date']}\n"
            f"[bold]Thread ID:[/bold] {email['thread_id']}\n"
            f"[bold]Labels:[/bold] {', '.join(email['labels'])}\n\n"
            f"[bold]Body:[/bold]\n{email['body'][:500]}...",
            title="Email Details",
            border_style="cyan"
        ))
        
        if 'draft' in email:
            console.print(Panel(
                email['draft'],
                title="Generated Draft",
                border_style="green"
            ))
    
    def show_stats(self):
        """Show cache statistics."""
        stats = self.agent.get_email_stats()
        
        table = Table(title="Cache Statistics")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        
        for key, value in stats.items():
            table.add_row(key.replace("_", " ").title(), str(value))
        
        console.print(table)
    
    def clear_cache(self):
        """Clear the Redis cache."""
        if Confirm.ask("Clear all cached data?"):
            self.agent.clear_cache()
            console.print("[green]✓ Cache cleared[/green]")

if __name__ == "__main__":
    try:
        interface = PlumaTestInterface()
        interface.run()
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        sys.exit(1)