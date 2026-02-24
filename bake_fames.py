import bpy
import os
import shutil

'''
Tested on Blender 4.5.3 LTS
*** Note that your render engine needs to be set to Cycles ***

OPERATING INSTRUCTIONS

1. Set your bake range below
2. To reduce render times, reduce the # of cycles samples 
3. To view progress go to Window --> Toggle System Console
'''
bake_frames = range(0, 11)

def framefile(filepath, frame):
    fn, ext = os.path.splitext(filepath)
    return "%s_%04d%s" % (fn, frame, ext)

context = bpy.context
obj = context.active_object

if not obj:
    raise RuntimeError("No active object.")

if obj.mode != 'OBJECT':
    bpy.ops.object.mode_set(mode='OBJECT')

obj.select_set(True)

# find image and make its node active
img = None
for mat_slot in obj.material_slots:
    mat = mat_slot.material
    if not mat or not mat.node_tree:
        continue
    for node in mat.node_tree.nodes:
        if node.type == 'TEX_IMAGE' and node.image:
            img = node.image
            mat.node_tree.nodes.active = node
            break
    if img:
        break

if not img:
    raise RuntimeError("No image texture node found.")

img_filepath_abs = bpy.path.abspath(img.filepath, library=img.library)

# save original, set low for baking, then restore
original_samples = bpy.context.scene.cycles.samples
bpy.context.scene.cycles.samples = 32

for f in bake_frames:
    print("Baking frame %d" % f)
    context.scene.frame_set(f)
    
    # Blender 4.x requires target argument
    try:
        bpy.ops.object.bake(target='IMAGE_TEXTURES')
    except TypeError:
        # fallback for older API
        bpy.ops.object.bake()
    
    img.save()
    img_filepath_new = framefile(img_filepath_abs, f)
    shutil.copyfile(img_filepath_abs, img_filepath_new)
    print("Saved %r" % img_filepath_new)

# restore original samples
bpy.context.scene.cycles.samples = original_samples
print("Samples restored to %d" % original_samples)
print("Baking Completed.")