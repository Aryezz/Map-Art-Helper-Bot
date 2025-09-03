from __future__ import annotations

import typing
import traceback
from datetime import datetime

import discord
from discord import ui
from discord.ext.commands import Bot
from discord.ui.select import BaseSelect

import sqla_db
from map_archive_entry import MapArtArchiveEntry, MapArtType, MapArtPalette


class BaseView(discord.ui.LayoutView):
    interaction: discord.Interaction | None = None
    message: discord.Message | None = None

    def __init__(self, user: discord.User | discord.Member, timeout: float = 60.0):
        super().__init__(timeout=timeout)
        # We set the user who invoked the command as the user who can interact with the view
        self.user = user

    # make sure that the view only processes interactions from the user who invoked the command
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user.id:
            await interaction.response.send_message(
                "You cannot interact with this view.", ephemeral=True
            )
            return False
        # update the interaction attribute when a valid interaction is received
        self.interaction = interaction
        return True

    # to handle errors we first notify the user that an error has occurred and then disable all components

    def _disable_all(self) -> None:
        # disable all components
        # so components that can be disabled are buttons and select menus
        for item in self.children:
            if isinstance(item, discord.ui.Button) or isinstance(item, BaseSelect):
                item.disabled = True

    # after disabling all components we need to edit the message with the new view
    # now when editing the message there are two scenarios:
    # 1. the view was never interacted with i.e in case of plain timeout here message attribute will come in handy
    # 2. the view was interacted with and the interaction was processed and we have the latest interaction stored in the interaction attribute
    async def _edit(self, **kwargs: typing.Any) -> None:
        if self.interaction is None and self.message is not None:
            # if the view was never interacted with and the message attribute is not None, edit the message
            await self.message.edit(**kwargs)
        elif self.interaction is not None:
            try:
                # if not already responded to, respond to the interaction
                await self.interaction.response.edit_message(**kwargs)
            except discord.InteractionResponded:
                # if already responded to, edit the response
                await self.interaction.edit_original_response(**kwargs)

    async def on_error(self, interaction: discord.Interaction, error: Exception, item: discord.ui.Item[BaseView]) -> None:
        tb = "".join(traceback.format_exception(type(error), error, error.__traceback__))
        message = f"An error occurred while processing the interaction for {str(item)}:\n```py\n{tb}\n```"
        # disable all components
        self._disable_all()
        # edit the message with the error message
        await self._edit(content=message, view=self)
        # stop the view
        self.stop()

    async def on_timeout(self) -> None:
        # disable all components
        self._disable_all()
        # edit the message with the new view
        await self._edit(view=self)


class MapAttributeEditorModal(discord.ui.Modal, title="Map Attribute Editor"):
    name = discord.ui.TextInput(label='Name')
    artists = discord.ui.TextInput(label='Artists')
    notes = discord.ui.TextInput(label='Notes', style=discord.TextStyle.paragraph, required=False)
    width = discord.ui.TextInput(label='Width')
    height = discord.ui.TextInput(label='Height')

    def __init__(self, view: 'MapEntityEditorView'):
        super().__init__()
        self.view = view

        self.name.default = str(self.view.entry.name)
        self.artists.default = ", ".join(self.view.entry.artists)
        self.notes.default = str(self.view.entry.notes)

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

        self.update_button()

    def update_button(self):
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

        self.update_button()

    def update_button(self):
        self.label = "Edit"

    async def callback(self, interaction: discord.Interaction[Bot]) -> None:
        await interaction.response.send_modal(MapDiscordAttributeEditorModal(self.view))


class MapEntityEditorView(BaseView):
    row = ui.ActionRow()

    def __init__(self, user, entry: MapArtArchiveEntry, timeout=180):
        super().__init__(user=user, timeout=timeout)
        self.entry = entry
        self.update_view()

    def update_view(self):
        self.clear_items()

        container = ui.Container()
        header = ui.Section(
            ui.TextDisplay("# Map Entry Settings <:mcmap:349454913526562816>"),
            accessory=ui.Thumbnail(self.entry.image_url)
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
                ui.TextDisplay("## Discord Attributes\n-# You probably don't have to change these, be careful!"),
                accessory=MapDiscordTextEditButton(self.entry)
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
