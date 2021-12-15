from sail import cli, util, ssh

from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

import click, os

def premium_init():
	'''Initialize premium modules if in a premium-enabled application'''
	try:
		is_premium = util.premium()
		if not is_premium:
			raise Exception('Not premium, nothing to init.')

		from sail.premium import backups
	except:
		pass

@cli.group()
def premium():
	'''Add, remove and update domains associated with your site'''
	pass

@premium.command()
@click.pass_context
def enable(ctx):
	'''Provision premium features for this application.'''
	config = util.config()
	root = util.find_root()
	license = util.get_sail_default('premium')
	email = util.get_sail_default('email')

	click.echo('# Setting up Sail Premium')

	if config.get('premium'):
		# raise click.ClickException('Premium features have already been enabled for this application.')
		pass

	if not license:
		raise click.ClickException('Premium license key not found. Set one with: sail config premium LICENSE_KEY')

	if not email:
		raise click.ClickException('Premium requires an e-mail configuration. Set one with: sail config email EMAIL_ADDRESS')

	click.echo('- Verifying license key')
	response = util.request('/premium/check/', json={
		'email': email,
		'license': license,
	})

	if not response:
		raise click.ClickException('Could not verify the premium license key.')

	click.echo('- Generating SSH keys')

	# Generate a key pair.
	key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
	private_key = key.private_bytes(
		serialization.Encoding.PEM,
		serialization.PrivateFormat.TraditionalOpenSSL,
		serialization.NoEncryption()
	).decode('utf8')

	public_key = key.public_key().public_bytes(
		serialization.Encoding.OpenSSH,
		serialization.PublicFormat.OpenSSH
	).decode('utf8')

	with open('%s/.sail/premium.key.pub' % root, 'w+') as f:
		f.write(public_key)
	os.chmod('%s/.sail/premium.key.pub' % root, 0o644)

	ctx.invoke(ssh.add, path='%s/.sail/premium.key.pub' % root, quiet=True)

	click.echo('- Verifying connection')
	response = util.request('/premium/enable/', json={
		'email': email,
		'license': license,
		'private_key': private_key,
		'namespace': config['namespace'],
	})

	click.echo('- Updating .sail/config.json')
	config['premium'] = license
	util.update_config(config)
