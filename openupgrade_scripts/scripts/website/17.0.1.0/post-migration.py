# Copyright 2024 Viindoo Technology Joint Stock Company (Viindoo)
# Copyright 2025 ForgeFlow S.L. (https://www.forgeflow.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from openupgradelib import openupgrade


def update_ir_attachment_urls(env):
    """Update ir_attachment URLs for SCSS files."""
    # Update user_values.scss files
    # Find assets with target path, get their current path, and update attachments with matching url
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE ir_attachment att
        SET url = '/_custom/web.assets_frontend/website/static/src/scss/options/user_values.scss'
        FROM ir_asset asset
        WHERE asset.target = '/website/static/src/scss/options/user_values.scss'
            AND att.url = asset.path
        """,
    )
    # Update user_color_palette.scss files
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE ir_attachment att
        SET url = '/_custom/web.assets_frontend/website/static/src/scss/options/colors/user_color_palette.scss'
        FROM ir_asset asset
        WHERE asset.target = '/website/static/src/scss/options/colors/user_color_palette.scss'
            AND att.url = asset.path
        """,
    )


def update_ir_asset_paths(env):
    """Update ir.asset paths for SCSS files."""
    # Update user_values.scss files
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE ir_asset
        SET path = '/_custom/web.assets_frontend/website/static/src/scss/options/user_values.scss'
        WHERE target = '/website/static/src/scss/options/user_values.scss'
        """,
    )
    # Update user_color_palette.scss files
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE ir_asset
        SET path = '/_custom/web.assets_frontend/website/static/src/scss/options/colors/user_color_palette.scss'
        WHERE target = '/website/static/src/scss/options/colors/user_color_palette.scss'
        """,
    )


@openupgrade.migrate()
def migrate(env, version):
    update_ir_attachment_urls(env)
    update_ir_asset_paths(env)
    openupgrade.load_data(env, "website", "17.0.1.0/noupdate_changes.xml")
