from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):

    _inherit = 'res.config.settings'

    # ----------------------------------------------------------
    # Properties
    # ----------------------------------------------------------

    @property
    def COLOR_FIELDS(self):
        return [
            'color_brand',
            'color_primary',
            'color_success',
            'color_info',
            'color_warning',
            'color_danger',
        ]
        
    @property
    def COLOR_ASSET_LIGHT_URL(self):
        return '/muk_web_colors/static/src/scss/colors_light.scss'
        
    @property
    def COLOR_BUNDLE_LIGHT_NAME(self):
        return 'web._assets_primary_variables'
        
    @property
    def COLOR_ASSET_DARK_URL(self):
        return '/muk_web_colors/static/src/scss/colors_dark.scss'
        
    @property
    def COLOR_BUNDLE_DARK_NAME(self):
        return 'web.assets_web_dark'

    #----------------------------------------------------------
    # Fields Light Mode
    #----------------------------------------------------------
    
    color_brand_light = fields.Char(
        string='Brand Light Color'
    )
    
    color_primary_light = fields.Char(
        string='Primary Light Color'
    )
    
    color_success_light = fields.Char(
        string='Success Light Color'
    )
    
    color_info_light = fields.Char(
        string='Info Light Color'
    )
    
    color_warning_light = fields.Char(
        string='Warning Light Color'
    )
    
    color_danger_light = fields.Char(
        string='Danger Light Color'
    )

    #----------------------------------------------------------
    # Fields Dark Mode
    #----------------------------------------------------------
    
    color_brand_dark = fields.Char(
        string='Brand Dark Color'
    )
    
    color_primary_dark = fields.Char(
        string='Primary Dark Color'
    )
    
    color_success_dark = fields.Char(
        string='Success Dark Color'
    )
    
    color_info_dark = fields.Char(
        string='Info Dark Color'
    )
    
    color_warning_dark = fields.Char(
        string='Warning Dark Color'
    )
    
    color_danger_dark = fields.Char(
        string='Danger Dark Color'
    )
    
    #----------------------------------------------------------
    # Helper
    #----------------------------------------------------------
    
    def _get_light_color_values(self):
        return {}
        
    def _get_dark_color_values(self):
        return {}
        
    def _set_light_color_values(self, values):
        return values
        
    def _set_dark_color_values(self, values):
        return values
    
    def _detect_light_color_change(self):
        return False
        
    def _detect_dark_color_change(self):
        return False
        
    def _replace_light_color_values(self):
        return False
        
    def _replace_dark_color_values(self):
        return False
    
    def _reset_light_color_assets(self):
        custom_url = '/_custom/web._assets_primary_variables/muk_web_colors/static/src/scss/colors_light.scss'
        self.env['ir.attachment'].sudo().search([('url', '=', custom_url)]).unlink()
        self.env['ir.asset'].sudo().search([('path', '=', custom_url)]).unlink()
        
    def _reset_dark_color_assets(self):
        custom_url = '/_custom/web.assets_web_dark/muk_web_colors/static/src/scss/colors_dark.scss'
        self.env['ir.attachment'].sudo().search([('url', '=', custom_url)]).unlink()
        self.env['ir.asset'].sudo().search([('path', '=', custom_url)]).unlink()
        
    #----------------------------------------------------------
    # Action
    #----------------------------------------------------------
    
    def action_reset_light_color_assets(self):
        self._reset_light_color_assets()
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
    
    def action_reset_dark_color_assets(self):
        self._reset_dark_color_assets()
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
    
    #----------------------------------------------------------
    # Functions
    #----------------------------------------------------------

    def get_values(self):
        res = super().get_values()
        res = self._set_light_color_values(res)
        res = self._set_dark_color_values(res)
        return res

    def set_values(self):
        res = super().set_values()
        return res
