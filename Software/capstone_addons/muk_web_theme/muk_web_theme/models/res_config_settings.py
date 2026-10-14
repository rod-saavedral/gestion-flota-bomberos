from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):

    _inherit = 'res.config.settings'

    @property
    def THEME_COLOR_FIELDS(self):
        return [
            'color_appsmenu_text',
            'color_appbar_text',
            'color_appbar_active',
            'color_appbar_background',
        ]

    @property
    def COLOR_ASSET_THEME_URL(self):
        return '/muk_web_theme/static/src/scss/colors.scss'
        
    @property
    def COLOR_BUNDLE_THEME_NAME(self):
        return 'web._assets_primary_variables'
    
    #----------------------------------------------------------
    # Fields
    #----------------------------------------------------------
    
    theme_favicon = fields.Binary(
        related='company_id.favicon',
        readonly=False
    )
    
    theme_background_image = fields.Binary(
        related='company_id.background_image',
        readonly=False
    )
    
    theme_color_appsmenu_text = fields.Char(
        string='Apps Menu Text Color'
    )
    
    theme_color_appbar_text = fields.Char(
        string='AppsBar Text Color'
    )
    
    theme_color_appbar_active = fields.Char(
        string='AppsBar Active Color'
    )
    
    theme_color_appbar_background = fields.Char(
        string='AppsBar Background Color'
    )
    
    #----------------------------------------------------------
    # Helper
    #----------------------------------------------------------
    
    def _get_theme_color_values(self):
        return {}
        
    def _set_theme_color_values(self, values):
        return values

    def _detect_theme_color_change(self):
        return False

    def _replace_theme_color_values(self):
        return False

    def _reset_theme_color_assets(self):
        custom_url = '/_custom/web._assets_primary_variables/muk_web_theme/static/src/scss/colors.scss'
        self.env['ir.attachment'].sudo().search([('url', '=', custom_url)]).unlink()
        self.env['ir.asset'].sudo().search([('path', '=', custom_url)]).unlink()
    
    #----------------------------------------------------------
    # Action
    #----------------------------------------------------------
    
    def action_reset_theme_color_assets(self):
        self._reset_light_color_assets()
        self._reset_dark_color_assets()
        self._reset_theme_color_assets()
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
    
    #----------------------------------------------------------
    # Functions
    #----------------------------------------------------------

    def get_values(self):
        res = super().get_values()
        res = self._set_theme_color_values(res)
        return res

    def set_values(self):
        res = super().set_values()
        return res
