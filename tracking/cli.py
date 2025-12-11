import click
import json
from typing import Optional
from tabulate import tabulate
from .database import Database


@click.group()
@click.option('--db', default='tracking.db', help='Path to SQLite database')
@click.pass_context
def cli(ctx, db):
    """Email tracking CLI tool."""
    ctx.ensure_object(dict)
    ctx.obj['db'] = Database(db)


@cli.group()
def campaign():
    """Campaign management commands."""
    pass


@cli.group()
def message():
    """Message management commands."""
    pass


@cli.group()
def report():
    """Report and analytics commands."""
    pass


# Campaign commands

@campaign.command('create')
@click.option('--name', required=True, help='Campaign name')
@click.option('--template-id', type=int, help='Template ID')
@click.pass_context
def create_campaign(ctx, name, template_id):
    """Create a new campaign."""
    db = ctx.obj['db']
    campaign_id = db.create_campaign(name, template_id)
    click.echo(f"Campaign created with ID: {campaign_id}")


@campaign.command('list')
@click.pass_context
def list_campaigns(ctx):
    """List all campaigns."""
    db = ctx.obj['db']
    campaigns = db.get_all_campaigns()
    
    if not campaigns:
        click.echo("No campaigns found.")
        return
    
    table_data = []
    for campaign in campaigns:
        metrics = db.get_campaign_metrics(campaign['id'])
        table_data.append([
            campaign['id'],
            campaign['name'],
            metrics['total'],
            metrics['sent'],
            metrics['opened'],
            metrics['clicked'],
            metrics['bounced'],
            metrics['open_rate'],
            metrics['click_rate'],
            metrics['bounce_rate'],
        ])
    
    headers = ['ID', 'Name', 'Total', 'Sent', 'Opened', 'Clicked', 'Bounced', 'Open %', 'Click %', 'Bounce %']
    click.echo(tabulate(table_data, headers=headers, tablefmt='grid'))


@campaign.command('show')
@click.argument('campaign_id', type=int)
@click.pass_context
def show_campaign(ctx, campaign_id):
    """Show campaign details."""
    db = ctx.obj['db']
    campaign = db.get_campaign(campaign_id)
    
    if not campaign:
        click.echo(f"Campaign {campaign_id} not found.")
        return
    
    metrics = db.get_campaign_metrics(campaign_id)
    
    click.echo(f"\n=== Campaign {campaign_id}: {campaign['name']} ===")
    click.echo(f"Template ID: {campaign['template_id']}")
    click.echo(f"Created: {campaign['created_at']}")
    click.echo(f"\nMetrics:")
    click.echo(f"  Total: {metrics['total']}")
    click.echo(f"  Queued: {metrics['queued']}")
    click.echo(f"  Sent: {metrics['sent']}")
    click.echo(f"  Opened: {metrics['opened']} ({metrics['open_rate']}%)")
    click.echo(f"  Clicked: {metrics['clicked']} ({metrics['click_rate']}%)")
    click.echo(f"  Bounced: {metrics['bounced']} ({metrics['bounce_rate']}%)")
    
    if metrics['bounce_reasons']:
        click.echo(f"\nBounce Reasons:")
        for reason, count in metrics['bounce_reasons'].items():
            click.echo(f"  {reason}: {count}")


@campaign.command('messages')
@click.argument('campaign_id', type=int)
@click.option('--limit', default=20, help='Number of messages to show')
@click.option('--offset', default=0, help='Offset for pagination')
@click.pass_context
def campaign_messages(ctx, campaign_id, limit, offset):
    """Show messages for a campaign."""
    db = ctx.obj['db']
    campaign = db.get_campaign(campaign_id)
    
    if not campaign:
        click.echo(f"Campaign {campaign_id} not found.")
        return
    
    messages = db.get_campaign_messages(campaign_id, limit, offset)
    
    if not messages:
        click.echo("No messages found.")
        return
    
    table_data = []
    for msg in messages:
        table_data.append([
            msg['id'],
            msg['recipient_email'],
            msg['status'],
            msg['tracking_token'][:8] + '...',
            msg['sent_at'][:10] if msg['sent_at'] else '-',
            msg['opened_at'][:10] if msg['opened_at'] else '-',
            msg['bounced_at'][:10] if msg['bounced_at'] else '-',
        ])
    
    headers = ['ID', 'Email', 'Status', 'Token', 'Sent', 'Opened', 'Bounced']
    click.echo(tabulate(table_data, headers=headers, tablefmt='grid'))


@campaign.command('delete')
@click.argument('campaign_id', type=int)
@click.confirmation_option(prompt='Are you sure you want to delete this campaign?')
@click.pass_context
def delete_campaign_cmd(ctx, campaign_id):
    """Delete a campaign and all related data."""
    db = ctx.obj['db']
    campaign = db.get_campaign(campaign_id)
    
    if not campaign:
        click.echo(f"Campaign {campaign_id} not found.")
        return
    
    db.delete_campaign(campaign_id)
    click.echo(f"Campaign {campaign_id} deleted.")


@campaign.command('export')
@click.argument('campaign_id', type=int)
@click.option('--output', default=None, help='Output file path')
@click.pass_context
def export_campaign(ctx, campaign_id, output):
    """Export campaign data to CSV."""
    db = ctx.obj['db']
    campaign = db.get_campaign(campaign_id)
    
    if not campaign:
        click.echo(f"Campaign {campaign_id} not found.")
        return
    
    csv_data = db.export_campaign_to_csv(campaign_id)
    
    if output:
        with open(output, 'w') as f:
            f.write(csv_data)
        click.echo(f"Campaign exported to {output}")
    else:
        click.echo(csv_data)


# Message commands

@message.command('create')
@click.option('--campaign-id', type=int, required=True, help='Campaign ID')
@click.option('--email', required=True, help='Recipient email')
@click.option('--token', help='Tracking token (auto-generated if not provided)')
@click.option('--template-id', type=int, help='Template ID')
@click.pass_context
def create_message(ctx, campaign_id, email, token, template_id):
    """Create a new message."""
    db = ctx.obj['db']
    
    campaign = db.get_campaign(campaign_id)
    if not campaign:
        click.echo(f"Campaign {campaign_id} not found.")
        return
    
    import uuid
    tracking_token = token or str(uuid.uuid4())
    
    message_id = db.create_message(
        campaign_id=campaign_id,
        recipient_email=email,
        tracking_token=tracking_token,
        template_id=template_id
    )
    
    click.echo(f"Message created with ID: {message_id}")
    click.echo(f"Tracking token: {tracking_token}")


@message.command('show')
@click.argument('message_id', type=int)
@click.pass_context
def show_message(ctx, message_id):
    """Show message details."""
    db = ctx.obj['db']
    message = db.get_message(message_id)
    
    if not message:
        click.echo(f"Message {message_id} not found.")
        return
    
    click.echo(f"\n=== Message {message_id} ===")
    click.echo(f"Email: {message['recipient_email']}")
    click.echo(f"Campaign ID: {message['campaign_id']}")
    click.echo(f"Status: {message['status']}")
    click.echo(f"Tracking Token: {message['tracking_token']}")
    click.echo(f"\nTimestamps:")
    click.echo(f"  Queued: {message['queued_at']}")
    click.echo(f"  Sent: {message['sent_at']}")
    click.echo(f"  Opened: {message['opened_at']}")
    click.echo(f"  Clicked: {message['clicked_at']}")
    click.echo(f"  Bounced: {message['bounced_at']}")
    
    if message['bounce_reason']:
        click.echo(f"\nBounce Reason: {message['bounce_reason']}")
        click.echo(f"Bounce Type: {message['bounce_type']}")
    
    if message['error_message']:
        click.echo(f"\nError: {message['error_message']}")


@message.command('mark-sent')
@click.argument('message_id', type=int)
@click.pass_context
def mark_sent_cmd(ctx, message_id):
    """Mark message as sent."""
    db = ctx.obj['db']
    message = db.get_message(message_id)
    
    if not message:
        click.echo(f"Message {message_id} not found.")
        return
    
    db.update_message_sent(message_id)
    click.echo(f"Message {message_id} marked as sent.")


@message.command('mark-opened')
@click.argument('message_id', type=int)
@click.pass_context
def mark_opened_cmd(ctx, message_id):
    """Mark message as opened."""
    db = ctx.obj['db']
    message = db.get_message(message_id)
    
    if not message:
        click.echo(f"Message {message_id} not found.")
        return
    
    db.update_message_opened(message_id)
    click.echo(f"Message {message_id} marked as opened.")


@message.command('mark-clicked')
@click.argument('message_id', type=int)
@click.pass_context
def mark_clicked_cmd(ctx, message_id):
    """Mark message as clicked."""
    db = ctx.obj['db']
    message = db.get_message(message_id)
    
    if not message:
        click.echo(f"Message {message_id} not found.")
        return
    
    db.update_message_clicked(message_id)
    click.echo(f"Message {message_id} marked as clicked.")


@message.command('mark-bounced')
@click.argument('message_id', type=int)
@click.option('--reason', required=True, help='Bounce reason')
@click.option('--type', 'bounce_type', default='permanent', help='Bounce type')
@click.pass_context
def mark_bounced_cmd(ctx, message_id, reason, bounce_type):
    """Mark message as bounced."""
    db = ctx.obj['db']
    message = db.get_message(message_id)
    
    if not message:
        click.echo(f"Message {message_id} not found.")
        return
    
    db.update_message_bounced(message_id, reason, bounce_type)
    click.echo(f"Message {message_id} marked as bounced.")


# Report commands

@report.command('summary')
@click.pass_context
def report_summary(ctx):
    """Show summary of all campaigns."""
    db = ctx.obj['db']
    campaigns = db.get_all_campaigns()
    
    if not campaigns:
        click.echo("No campaigns found.")
        return
    
    total_messages = 0
    total_sent = 0
    total_opened = 0
    total_clicked = 0
    total_bounced = 0
    
    for campaign in campaigns:
        metrics = db.get_campaign_metrics(campaign['id'])
        total_messages += metrics['total']
        total_sent += metrics['sent']
        total_opened += metrics['opened']
        total_clicked += metrics['clicked']
        total_bounced += metrics['bounced']
    
    click.echo("\n=== Email Tracking Summary ===")
    click.echo(f"Total Campaigns: {len(campaigns)}")
    click.echo(f"Total Messages: {total_messages}")
    click.echo(f"Total Sent: {total_sent}")
    click.echo(f"Total Opened: {total_opened}")
    click.echo(f"Total Clicked: {total_clicked}")
    click.echo(f"Total Bounced: {total_bounced}")
    
    if total_sent > 0:
        click.echo(f"\nAggregate Rates:")
        click.echo(f"  Open Rate: {round((total_opened / total_sent) * 100, 2)}%")
        click.echo(f"  Click Rate: {round((total_clicked / total_sent) * 100, 2)}%")
        click.echo(f"  Bounce Rate: {round((total_bounced / total_messages) * 100, 2)}%")


@report.command('bounces')
@click.option('--campaign-id', type=int, help='Filter by campaign ID')
@click.option('--limit', default=50, help='Number of results to show')
@click.pass_context
def report_bounces(ctx, campaign_id, limit):
    """Show bounce report."""
    db = ctx.obj['db']
    
    if campaign_id:
        campaigns = [db.get_campaign(campaign_id)]
        if not campaigns[0]:
            click.echo(f"Campaign {campaign_id} not found.")
            return
    else:
        campaigns = db.get_all_campaigns()
    
    table_data = []
    count = 0
    
    for campaign in campaigns:
        messages = db.get_campaign_messages(campaign['id'], limit=1000)
        for msg in messages:
            if msg['status'] == 'bounced':
                table_data.append([
                    msg['id'],
                    campaign['name'],
                    msg['recipient_email'],
                    msg['bounce_type'],
                    msg['bounce_reason'],
                    msg['bounced_at'][:10] if msg['bounced_at'] else '-',
                ])
                count += 1
                if count >= limit:
                    break
        if count >= limit:
            break
    
    if not table_data:
        click.echo("No bounces found.")
        return
    
    headers = ['ID', 'Campaign', 'Email', 'Type', 'Reason', 'Date']
    click.echo(tabulate(table_data, headers=headers, tablefmt='grid'))


if __name__ == '__main__':
    cli(obj={})
