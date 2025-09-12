from __future__ import annotations

import traceback
from datetime import datetime

import discord
from discord import ui
from discord.ext.commands import Bot

import config
import sqla_db
from cogs.base_view import BaseView
from map_archive_entry import MapArtArchiveEntry, MapArtType, MapArtPalette


class MapAttributeEditorModal(discord.ui.Modal, title="Map Attribute Editor"):
    name = discord.ui.TextInput(label='Name')
    artists = discord.ui.TextInput(label='Artists')
    notes = discord.ui.TextInput(label='Notes', style=discord.TextStyle.paragraph, required=False)
    width = discord.ui.TextInput(label='Width')
    height = discord.ui.TextInput(label='Height')

    def __init__(self, view: 'MapEntityEditorView'):
        super().__init__()
        self.view = view

        self.name.default = self.view.entry.name.replace("\n", "")
        self.artists.default = ", ".join(self.view.entry.artists).replace("\n", "")
        self.notes.default = self.view.entry.notes

        self.width.default = str(self.view.entry.width)
        self.height.default = str(self.view.entry.height)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        valid = self.width.value.isnumeric() and int(self.width.value) >= 1 and self.height.value.isnumeric() and int(self.height.value) >= 1

        if valid:
            self.view.entry.name = self.name.value
            self.view.entry.artists = [a.strip() for a in self.artists.value.split(", ")]
            self.view.entry.notes = self.notes.value

            self.view.entry.width = int(self.width.value)
            self.view.entry.height = int(self.height.value)

            self.view.update_view()
            await interaction.response.edit_message(view=self.view)
        else:
            await interaction.response.send_message("Entered size is not valid, discarding", ephemeral=True)

    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        await interaction.response.send_message('Oops! Something went wrong.', ephemeral=True)

        # Make sure we know what the error actually is
        traceback.print_exception(type(error), error, error.__traceback__)


class MapTextEditButton(ui.Button['MapEntityEditorView']):
    def __init__(self, entry: MapArtArchiveEntry):
        super().__init__(style=discord.ButtonStyle.grey)
        self.entry = entry
        self.label = "Edit"

    async def callback(self, interaction: discord.Interaction[Bot]) -> None:
        await interaction.response.send_modal(MapAttributeEditorModal(self.view))


class MapTypeSelection(ui.ActionRow['MapEntityEditorView']):
    map_type_options = [
        discord.SelectOption(label="Flat"),
        discord.SelectOption(label="Dual-Layered"),
        discord.SelectOption(label="Staircased"),
        discord.SelectOption(label="Semi-Staircased"),
        discord.SelectOption(label="Unknown"),
    ]

    def __init__(self, entry: MapArtArchiveEntry):
        super().__init__()
        self.entry = entry
        self.update_options()

    def update_options(self):
        for option in self.select_map_type.options:
            option.default = option.value.lower() == self.entry.map_type.value

    @ui.select(placeholder='Select Map Type', options=map_type_options)
    async def select_map_type(self, interaction: discord.Interaction[Bot], select: discord.ui.Select) -> None:
        self.entry.map_type = MapArtType(select.values[0].lower())
        self.update_options()
        await interaction.response.edit_message(view=self.view)


class MapPaletteSelection(ui.ActionRow['MapEntityEditorView']):
    map_palette_options = [
        discord.SelectOption(label="Full colour"),
        discord.SelectOption(label="Two-colour"),
        discord.SelectOption(label="Carpet only"),
        discord.SelectOption(label="Greyscale"),
        discord.SelectOption(label="Unknown"),
    ]

    def __init__(self, entry: MapArtArchiveEntry):
        super().__init__()
        self.entry = entry
        self.update_options()

    def update_options(self):
        for option in self.select_map_palette.options:
            option.default = option.value.lower() == self.entry.palette.value

    @ui.select(placeholder='Select Map Type', options=map_palette_options)
    async def select_map_palette(self, interaction: discord.Interaction[Bot], select: discord.ui.Select) -> None:
        self.entry.palette = MapArtPalette(select.values[0].lower())
        self.update_options()
        await interaction.response.edit_message(view=self.view)


class MapDiscordAttributeEditorModal(discord.ui.Modal, title="Map Attribute Editor"):
    author_id = discord.ui.TextInput(label='Author ID')
    message_id = discord.ui.TextInput(label='Message ID')
    image_url = discord.ui.TextInput(label='Image URL')
    create_date = discord.ui.TextInput(label='Create Date')

    def __init__(self, view: 'MapEntityEditorView'):
        super().__init__()
        self.view = view

        self.author_id.default = str(self.view.entry.author_id)
        self.message_id.default = str(self.view.entry.message_id)
        self.image_url.default = str(self.view.entry.image_url)
        self.create_date.default = str(self.view.entry.create_date)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        valid = self.message_id.value.isnumeric() and self.author_id.value.isnumeric()

        date = None
        try:
            date = datetime.fromisoformat(self.create_date.value)
        except ValueError:
            valid = False

        if valid:
            self.view.entry.author_id = int(self.author_id.value)
            self.view.entry.message_id = int(self.message_id.value)
            self.view.entry.image_url = self.image_url.value
            self.view.entry.create_date = date

            self.view.update_view()
            await interaction.response.edit_message(view=self.view)
        else:
            await interaction.response.send_message("Entered attributes are not valid, discarding", ephemeral=True)

    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        await interaction.response.send_message('Oops! Something went wrong.', ephemeral=True)

        # Make sure we know what the error actually is
        traceback.print_exception(type(error), error, error.__traceback__)


class MapDiscordTextEditButton(ui.Button['MapEntityEditorView']):
    def __init__(self, entry: MapArtArchiveEntry):
        super().__init__(style=discord.ButtonStyle.red)
        self.entry = entry
        self.label = "Edit"

    async def callback(self, interaction: discord.Interaction[Bot]) -> None:
        await interaction.response.send_modal(MapDiscordAttributeEditorModal(self.view))


class FlagEntryButton(ui.Button['MapEntityEditorView']):
    def __init__(self, entry: MapArtArchiveEntry):
        super().__init__(style=discord.ButtonStyle.red)
        self.entry = entry

        self.update_button()

    def update_button(self):
        if not self.entry.flagged:
            self.label = "Flag Entry"
            self.style = discord.ButtonStyle.red
        else:
            self.label = "Unflag Entry"
            self.style = discord.ButtonStyle.green

    async def callback(self, interaction: discord.Interaction[Bot]) -> None:
        self.entry.flagged = not self.entry.flagged
        self.update_button()
        await interaction.response.edit_message(view=self.view)


class DeleteEntryButton(ui.Button['MapEntityEditorView']):
    def __init__(self, entry: MapArtArchiveEntry):
        super().__init__(style=discord.ButtonStyle.red)
        self.entry = entry
        self.label = "Delete Entry"
        self.you_sure = False

    async def callback(self, interaction: discord.Interaction[Bot]) -> None:
        if not self.you_sure:
            self.label = "YOU SURE?"
            self.you_sure = True
            await interaction.response.edit_message(view=self.view)
        else:
            await self.view.delete_entry(interaction)


class MapEntityEditorView(BaseView):
    row = ui.ActionRow()

    def __init__(self, user, entry: MapArtArchiveEntry, message_content: str, timeout=180):
        super().__init__(user=user, timeout=timeout)
        self.entry = entry
        self.message_content = message_content
        self.update_view()

    def update_view(self):
        self.clear_items()

        thumbnail_url = self.entry.image_url or "https://minecraft.wiki/images/Barrier_%28held%29_JE2_BE2.png"

        container = ui.Container()
        header = ui.Section(
            ui.TextDisplay(
                f"# Map Entry Settings <:mcmap:349454913526562816>\n" +
                f"[Jump to message]({self.entry.link})\n" +
                "### Message text\n" +
                ("> " + self.message_content.replace("\n", "\n> ") if self.message_content else "")
            ),
            accessory=ui.Thumbnail(thumbnail_url, spoiler=self.entry.flagged)
        )
        container.add_item(header)

        container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.large))

        container.add_item(
            ui.Section(
                ui.TextDisplay(
                    f"## General Attributes\n" +
                    f"### Name\n{self.entry.name}\n" +
                    f"### Size\n{self.entry.width} x {self.entry.height}\n" +
                    f"### Artists\n" + "\n".join(f"* {artist}" for artist in self.entry.artists) + "\n" +
                    f"### Notes\n" +
                    ("\n".join("> " + line for line in self.entry.notes.split("\n")) if self.entry.notes else "-")
                ),
                accessory=MapTextEditButton(self.entry)
            )
        )

        container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))

        container.add_item(ui.TextDisplay("### Map Type\n-# The map type, this will most commonly be either flat or staircased"))
        container.add_item(MapTypeSelection(self.entry))

        container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))

        container.add_item(ui.TextDisplay("### Map Palette\n-# The map palette, this will most commonly be either carpet only of full-colour"))
        container.add_item(MapPaletteSelection(self.entry))

        container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        container.add_item(
            ui.Section(
                ui.TextDisplay("## Administrative Stuff\n-# You probably don't have to change these, be careful!"),
                accessory=MapDiscordTextEditButton(self.entry)
            )
        )
        container.add_item(
            ui.ActionRow(
                FlagEntryButton(self.entry),
                DeleteEntryButton(self.entry),
            )
        )

        self.add_item(container)
        self.add_item(self.row)

    @row.button(label='Save', style=discord.ButtonStyle.green)
    async def save_button(self, interaction: discord.Interaction[Bot], button: ui.Button) -> None:
        await interaction.response.edit_message(view=self)

        async with sqla_db.Session() as db:
            await db.add_maps([self.entry])

        await interaction.followup.send(f'Map art saved', ephemeral=True)
        self.stop()
        await interaction.delete_original_response()

    @row.button(label='Cancel', style=discord.ButtonStyle.grey)
    async def cancel_button(self, interaction: discord.Interaction[Bot], button: ui.Button) -> None:
        await interaction.response.edit_message(view=self)
        await interaction.followup.send(f'Edit cancelled', ephemeral=True)
        self.stop()
        await interaction.delete_original_response()

    async def delete_entry(self, interaction: discord.Interaction[Bot]) -> None:
        await interaction.response.edit_message(view=self)

        async with sqla_db.Session() as db:
            await db.delete_maps([self.entry])

        await interaction.followup.send(f'Map art deleted, [Link]({self.entry.link})')
        self.stop()
        await interaction.delete_original_response()

