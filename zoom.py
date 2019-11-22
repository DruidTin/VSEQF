import bpy
from . import timeline
from . import vseqf


def zoom_custom(begin, end, bottom=None, top=None, preroll=True):
    """Zooms to an area on the sequencer timeline by adding a temporary strip, zooming to it, then deleting that strip.
    Note that this function will retain selected and active sequences.
    Arguments:
        begin: The starting frame of the zoom area
        end: The ending frame of the zoom area
        bottom: The lowest visible channel
        top: The topmost visible channel
        preroll: If true, add a buffer before the beginning"""

    del bottom  #Add in someday...
    del top     #Add in someday...
    scene = bpy.context.scene
    selected = []

    #Find sequence editor, or create if not found
    try:
        sequences = bpy.context.sequences
    except:
        scene.sequence_editor_create()
        sequences = bpy.context.sequences

    #Save selected sequences and active strip because they will be overwritten
    for sequence in sequences:
        if sequence.select:
            selected.append(sequence)
            sequence.select = False
    active = timeline.current_active(bpy.context)

    begin = int(begin)
    end = int(end)

    #Determine preroll for the zoom
    zoomlength = end - begin
    if zoomlength > 60 and preroll:
        preroll = (zoomlength-60) / 10
    else:
        preroll = 0

    #Create a temporary sequence, zoom in on it, then delete it
    zoom_clip = scene.sequence_editor.sequences.new_effect(name='----vseqf-temp-zoom----', type='ADJUSTMENT', channel=1, frame_start=begin-preroll, frame_end=end)
    scene.sequence_editor.active_strip = zoom_clip
    for region in bpy.context.area.regions:
        if region.type == 'WINDOW':
            override = {'region': region, 'window': bpy.context.window, 'screen': bpy.context.screen, 'area': bpy.context.area, 'scene': bpy.context.scene}
            bpy.ops.sequencer.view_selected(override)
    bpy.ops.sequencer.delete()

    #Reset selected sequences and active strip
    for sequence in selected:
        sequence.select = True
    if active:
        bpy.context.scene.sequence_editor.active_strip = active


def zoom_cursor(self=None, context=None):
    """Zooms near the cursor based on the 'zoom_size' vseqf variable"""
    del self
    del context
    cursor = bpy.context.scene.frame_current
    zoom_custom(cursor, (cursor + bpy.context.scene.vseqf.zoom_size))


class VSEQFQuickZoomsMenu(bpy.types.Menu):
    """Pop-up menu for sequencer zoom shortcuts"""
    bl_idname = "VSEQF_MT_quickzooms_menu"
    bl_label = "Quick Zooms"

    def draw(self, context):
        scene = context.scene
        layout = self.layout

        layout.operator('vseqf.quickzooms', text='Zoom All Strips').area = 'all'
        layout.operator('vseqf.quickzooms', text='Zoom To Timeline').area = 'timeline'
        selected_sequences = timeline.current_selected(bpy.context)
        if len(selected_sequences) > 0:
            #Only show if a sequence is selected
            layout.operator('vseqf.quickzooms', text='Zoom Selected').area = 'selected'

        layout.operator('vseqf.quickzooms', text='Zoom Cursor').area = 'cursor'
        layout.prop(scene.vseqf, 'zoom_size', text="Size")
        layout.operator('vseqf.quickzoom_add', text='Save Current Zoom')
        if len(scene.vseqf.zoom_presets) > 0:
            layout.menu('VSEQF_MT_quickzoom_preset_menu')

        layout.separator()
        layout.operator('vseqf.quickzooms', text='Zoom 2 Seconds').area = '2'
        layout.operator('vseqf.quickzooms', text='Zoom 10 Seconds').area = '10'
        layout.operator('vseqf.quickzooms', text='Zoom 30 Seconds').area = '30'
        layout.operator('vseqf.quickzooms', text='Zoom 1 Minute').area = '60'
        layout.operator('vseqf.quickzooms', text='Zoom 2 Minutes').area = '120'
        layout.operator('vseqf.quickzooms', text='Zoom 5 Minutes').area = '300'
        layout.operator('vseqf.quickzooms', text='Zoom 10 Minutes').area = '600'


class VSEQFQuickZoomPresetMenu(bpy.types.Menu):
    """Menu for saved zoom presets"""
    bl_idname = "VSEQF_MT_quickzoom_preset_menu"
    bl_label = "Zoom Presets"

    def draw(self, context):
        del context
        scene = bpy.context.scene
        layout = self.layout
        split = layout.split()
        column = split.column()
        for zoom in scene.vseqf.zoom_presets:
            column.operator('vseqf.quickzoom_preset', text=zoom.name).name = zoom.name
        column.separator()
        column.operator('vseqf.quickzoom_clear', text='Clear All')
        column = split.column()
        for zoom in scene.vseqf.zoom_presets:
            column.operator('vseqf.quickzoom_remove', text='X').name = zoom.name


class VSEQFQuickZoomPreset(bpy.types.Operator):
    """Zooms to a specific preset, given by name.
    Argument:
        name: String, the zoom preset to activate"""

    bl_idname = 'vseqf.quickzoom_preset'
    bl_label = "Zoom To QuickZoom Preset"

    name: bpy.props.StringProperty()

    def execute(self, context):
        scene = context.scene
        for zoom in scene.vseqf.zoom_presets:
            if zoom.name == self.name:
                zoom_custom(zoom.left, zoom.right, bottom=zoom.bottom, top=zoom.top, preroll=False)
                break
        return {'FINISHED'}


class VSEQFClearZooms(bpy.types.Operator):
    """Clears all zoom presets"""

    bl_idname = 'vseqf.quickzoom_clear'
    bl_label = 'Clear All Presets'

    def execute(self, context):
        scene = context.scene
        bpy.ops.ed.undo_push()
        for index, zoom_preset in reversed(list(enumerate(scene.vseqf.zoom_presets))):
            scene.vseqf.zoom_presets.remove(index)
        return{'FINISHED'}


class VSEQFRemoveZoom(bpy.types.Operator):
    """Removes a zoom from the preset list

    Argument:
        name: String, the name of the zoom preset to be removed"""

    bl_idname = 'vseqf.quickzoom_remove'
    bl_label = 'Remove Zoom Preset'

    name: bpy.props.StringProperty()

    def execute(self, context):
        scene = context.scene
        for index, zoom_preset in reversed(list(enumerate(scene.vseqf.zoom_presets))):
            if zoom_preset.name == self.name:
                bpy.ops.ed.undo_push()
                scene.vseqf.zoom_presets.remove(index)
        return{'FINISHED'}


class VSEQFAddZoom(bpy.types.Operator):
    """Stores the current vse zoom and position
    Argument:
        mode: String, determines where the preset is stored."""

    bl_idname = 'vseqf.quickzoom_add'
    bl_label = "Add Zoom Preset"

    mode: bpy.props.StringProperty()

    def execute(self, context):
        left, right, bottom, top = timeline.get_vse_position(context)
        scene = context.scene
        #name = "Frames "+str(int(round(left)))+'-'+str(int(round(right)))+', Channels '+str(int(round(bottom)))+'-'+str(int(round(top)))
        name = "Frames "+str(int(round(left)))+'-'+str(int(round(right)))
        bpy.ops.ed.undo_push()
        for index, zoom_preset in enumerate(scene.vseqf.zoom_presets):
            if zoom_preset.name == name:
                scene.vseqf.zoom_presets.move(index, len(scene.vseqf.zoom_presets) - 1)
                return{'FINISHED'}
        preset = scene.vseqf.zoom_presets.add()
        preset.name = name
        preset.left = left
        preset.right = right
        preset.bottom = bottom
        preset.top = top
        return{'FINISHED'}


class VSEQFQuickZooms(bpy.types.Operator):
    """Wrapper operator for zooming the sequencer in different ways
    Argument:
        area: String, determines the zoom method, can be set to:
            all: calls bpy.ops.sequencer.view_all()
            selected: calls bpy.ops.sequencer.view_selected()
            cursor: calls the zoom_cursor() function
            numerical value: zooms to the number of seconds given in the value"""
    bl_idname = 'vseqf.quickzooms'
    bl_label = 'VSEQF Quick Zooms'
    bl_description = 'Changes zoom level of the sequencer timeline'

    #Should be set to 'all', 'selected', cursor', or a positive number of seconds
    area: bpy.props.StringProperty()

    def execute(self, context):
        #return bpy.ops.view2d.smoothview("INVOKE_DEFAULT", xmin=0, xmax=10, ymin=0, ymax=10, wait_for_input=False)
        if self.area.isdigit():
            #Zoom value is a number of seconds
            scene = context.scene
            cursor = scene.frame_current
            zoom_custom(cursor, (cursor + (vseqf.get_fps(scene) * int(self.area))))
        elif self.area == 'timeline':
            scene = context.scene
            zoom_custom(scene.frame_start, scene.frame_end)
        elif self.area == 'all':
            bpy.ops.sequencer.view_all()
        elif self.area == 'selected':
            bpy.ops.sequencer.view_selected()
        elif self.area == 'cursor':
            zoom_cursor()
        return{'FINISHED'}


class VSEQFZoomPreset(bpy.types.PropertyGroup):
    """Property group to store a sequencer view position"""
    name: bpy.props.StringProperty(name="Preset Name", default="")
    left: bpy.props.FloatProperty(name="Leftmost Visible Frame", default=0.0)
    right: bpy.props.FloatProperty(name="Rightmost Visible Frame", default=300.0)
    bottom: bpy.props.FloatProperty(name="Bottom Visible Channel", default=0.0)
    top: bpy.props.FloatProperty(name="Top Visible Channel", default=5.0)