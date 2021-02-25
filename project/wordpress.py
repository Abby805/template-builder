import os
import os.path
import json
from collections import OrderedDict
from . import BaseProject
from .remote import RemoteProject


class Wordpress_vanilla(BaseProject):
    remote = 'https://wordpress.org/latest'
    install_dir = 'wordpress'

    @property
    def platformify(self):
        return super(Wordpress_vanilla, self).platformify + [
            # Install WordPress
            'cd {0} && curl {1} -o {2}.tar.gz'.format(self.builddir, self.remote, self.install_dir),
            # Release the tar and cleanup.
            'cd {0} && tar -xvf {1}.tar.gz && rm {1}.tar.gz'.format(self.builddir, self.install_dir),
            # Move Platform.sh files into `wordpress`.
            'cd {0} && mv wp-config.php {1} && mv wp-cli.yml {1}'.format(self.builddir, self.install_dir),
        ]

class Wordpress_bedrock(RemoteProject):
    major_version = '1'
    remote = 'https://github.com/roots/bedrock.git'

    @property
    def platformify(self):
        return super(Wordpress_bedrock, self).platformify + [
            'cd {0} && rm -rf .circleci && rm -rf .github'.format(self.builddir),
            'cd {0} && composer update'.format(self.builddir) + self.composer_defaults(),
        ]

class Wordpress_woocommerce(RemoteProject):
    major_version = '1'
    remote = 'https://github.com/roots/bedrock.git'

    @property
    def platformify(self):
        return super(Wordpress_woocommerce, self).platformify + [
            'cd {0} && rm -rf .circleci && rm -rf .github'.format(self.builddir),
            'cd {0} && composer require wpackagist-plugin/woocommerce wpackagist-plugin/jetpack'.format(self.builddir) + self.composer_defaults(),
        ]

class Wordpress_composer(RemoteProject):
    major_version = '5'
    remote = 'https://github.com/johnpbloch/wordpress.git'

    @property
    def platformify(self):

        def require_default_wppackages():
            # johnbloch/wordpress wraps around the default WordPress installation, which includes with it a few themes and plugins by default. 
            # Those packages are not automatically added via Composer, and thus not explcitly defined as packages.
            # This only becomes a problem once you try to install new themes/plugins, at which point there is a recopy somewhere that causes 
            #   a nested wp-content subdirectory containing those default packages: https://github.com/platformsh-templates/wordpress-composer/issues/7.
            # John Bloch recommends that the best way to avoid this is to commit those default packages, and that makes sense. So this function reads the 
            #   default packages from wp-content, and the composer requires them. 
            root = '/wordpress/wp-content/'
            namespace = {
                "themes": "wpackagist-theme",
                "plugins": "wpackagist-plugin"
            }

            defaultPackages = []

            installerPaths = [x for x in os.listdir(self.builddir + root) if os.path.isdir(self.builddir + root + x)]
            for path in installerPaths:
                installerPath = '{0}{1}{2}/'.format(self.builddir, root, path)
                [defaultPackages.append('{0}/{1}'.format(namespace[path], x)) for x in os.listdir(installerPath) if os.path.isdir(installerPath + x)]

            return ' '.join(defaultPackages)

        def wp_modify_composer(composer):
            # In order to both use the Wordpress default install location `wordpress` and
            # supply the Platform.sh-specific `wp-config.php` to that installation, a script is
            # added to the upstream composer.json to move that config file during composer install.
            composer['scripts'] = {
                'copywpconfig': [
                    "cp wp-config.php wordpress/"
                ],
                'post-install-cmd': "@copywpconfig"
            }

            composer['extra'] = {
                'installer-paths': {
                    r'wordpress/wp-content/plugins/{$name}': ['type:wordpress-plugin'],
                    r'wordpress/wp-content/themes/{$name}': ['type:wordpress-theme'],
                    r'wordpress/wp-content/mu-plugins/{$name}': ['type:wordpress-muplugin'],
                }
            }

            composer['repositories'] = [
                {
                    "type": "composer",
                    "url": "https://wpackagist.org"
                }
            ]
            return composer

        return super(Wordpress_composer, self).platformify + [
            (self.modify_composer, [wp_modify_composer]),
            'cd {0} && composer update'.format(self.builddir) + self.composer_defaults(),
            'cd {0} && composer require platformsh/config-reader wp-cli/wp-cli-bundle psy/psysh'.format(self.builddir) + self.composer_defaults(),
            'cd {0} && composer require {1}'.format(self.builddir, require_default_wppackages()) + self.composer_defaults(),
        ]
