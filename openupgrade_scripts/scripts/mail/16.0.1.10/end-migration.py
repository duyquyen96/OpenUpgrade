import os.path

from lxml import etree
from openupgradelib import openupgrade

from odoo.modules import get_manifest
from odoo.tools.misc import file_open


def is_xml_filename(filename):
    return os.path.splitext(filename)[1].lower() == ".xml"


def get_module_xml_files(module_name):
    return filter(is_xml_filename, get_manifest(module_name).get("data", []))


def find_record_data_path(model_name, module_name, xml_id):
    """
    Get the path of the XML data file containing the record.
    """
    for xml_file in get_module_xml_files(module_name):
        filepath = "/".join((module_name, xml_file))
        with file_open(filepath, "rb") as f:
            root = etree.parse(f)
            found = root.xpath(f'//record[@model="{model_name}"][@id="{xml_id}"]')
            if found:
                return filepath
    return None


def fill_all_null_mail_template_template_fs(env):
    """
    Fill the new template_fs field of all mail.template if it is null.

    The mail.template template_fs field must contain the path of the data file
    where it is defined (to allow for it to be reset to its default value).
    Fill empty values by searching for the mail templates (by xml id) in the
    XML files of the module that defines it.
    """
    env.cr.execute(
        """
        select mt.id, imd.module, imd.name
        from mail_template as mt
        inner join ir_model_data as imd on
            imd.model = 'mail.template' and
            imd.res_id = mt.id
        where mt.template_fs is null
        """
    )
    mail_template_model = env["mail.template"]
    for mail_template_id, module_name, template_name in env.cr.fetchall():
        template_fs = find_record_data_path("mail.template", module_name, template_name)
        if template_fs is not None:
            mail_template = mail_template_model.browse(mail_template_id)
            mail_template.template_fs = template_fs


def _mail_channel_privacy(env):
    """
    Since Odoo 16, configure a private channel can be complicated
    Therefore we Viindoo provide a module that can make thing easier
    Check it out at https://viindoo.com/apps/app/16.0/viin_mail_channel_privacy
    or if you can't find it, just go to https://viindoo.com/apps
    then search for 'viin_mail_channel_privacy' to test this feature.
    """
    if "is_private" not in env["mail.channel"]._fields:
        return
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE mail_channel
        SET is_private = true
        WHERE public = 'private' AND channel_type = 'channel'
        """,
    )
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE mail_channel
        SET group_public_id = NULL
        WHERE public = 'public' AND channel_type = 'channel'
        """,
    )


@openupgrade.migrate()
def migrate(env, version):
    _mail_channel_privacy(env)
    fill_all_null_mail_template_template_fs(env)
