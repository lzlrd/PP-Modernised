# PP Modernised

XSSheep's Pixel Perfection for Minecraft Java 26.3, with Bedrock support through Geyser, LabPBR maps for shaders and 3D block models.

Built on [Pixel Perfection Legacy](https://modrinth.com/resourcepack/pixel-perfection-legacy) 26.3-97.2 by Nova_Wostra, with [Pixel Perfection CE](https://github.com/Athemis/PixelPerfectionCE) folded in where PPL has no texture.

## What it adds over PPL 26.3

- **Loads cleanly on 26.3.** Fixes the errors PPL 26.3-97.2 throws: every log and stem rendered as a missing model, plus broken spawner, vault, lantern and bar models, out-of-range animation frames and missing sounds. See the commit history for the full list.
- **Missing 26.3 textures.** Shulker box blocks, the conduit, trim palettes, the dry foliage colormap, new particles and new GUI pieces. Most are built from the pack's own art. [CONTENT_STATUS.md](CONTENT_STATUS.md) lists where each one comes from.
- **3D models.** Flowers, saplings, ladders, raised rails, chains, lily pads, roots and their potted versions get 1px of depth, extruded from their textures.
- **LabPBR 1.3.** `_n` and `_s` maps for 3,288 block, item and entity textures: normals, parallax height, AO, smoothness, F0 and metal IDs, porosity/SSS and emission. For Iris shader packs set to LabPBR, including path tracers.
- **Bedrock / Geyser.** A converted `.mcpack` with Vibrant Visuals PBR, animated block textures and Geyser custom item mappings for Dungeons and Taverns keys.

## Install

**Java 26.3:** put `PP-Modernised.zip` in `resourcepacks/`. For shaders, install Iris and pick a LabPBR shader pack. In Complementary, set RP Support to labPBR.

**Server (Paper/Leaf):** host the zip and set `resource-pack`, `resource-pack-sha1` and `resource-pack-id` in `server.properties`.

**Geyser:** put `pp_modernised.mcpack` in `plugins/Geyser-Spigot/packs/` and `pp_modernised.json` in `plugins/Geyser-Spigot/custom_mappings/`, keep `enable-custom-content: true`, and restart the server. The mappings cover Dungeons and Taverns keys and do nothing on servers without it. Bedrock players see the PBR when Vibrant Visuals is on.

Bedrock can't change vanilla block shapes, so the 3D models are Java-only. Random block variants and the quiver CIT are also Java-only.

## Optional mods (Java)

- [Continuity](https://modrinth.com/mod/continuity): connected glass and bookshelves (OptiFine CTM format).
- [Entity Texture Features](https://modrinth.com/mod/entitytexturefeatures): random and emissive mob textures.

## Build

```sh
tools/build_java.sh . build                  # build/PP-Modernised.zip
java -jar Thunder.jar nogui --input build/PP-Modernised.zip
python3 tools/gen_bedrock.py <thunder output dir> build/PP-Modernised <Thunder textures.json> <bedrock-samples textures dir> <Dungeons and Taverns datapack dir> 1.0.0 build/bedrock
(cd build/bedrock/PP-Modernised && zip -r ../pp_modernised.mcpack .)  # mappings: build/bedrock/geyser_custom_mappings/pp_modernised.json
```

The other scripts in `tools/` are the one-off generators and checks used to make this version. Each one documents its usage at the top of the file.

## Licence

[CC BY-SA 4.0](LICENSE.md). See [CREDITS.md](CREDITS.md).
