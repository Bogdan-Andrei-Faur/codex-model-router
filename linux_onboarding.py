"""First-run GTK import, using the same guarded migration as the macOS package."""
from application_layout import bootstrap
from installation_migration import import_legacy, MigrationError


def error_detail(error):
    if isinstance(error, MigrationError):
        return str(error)
    if isinstance(error, PermissionError):
        return 'No tienes permiso para leer la instalación anterior o guardar los datos nuevos. Los datos existentes se conservan.'
    return 'No se pudo completar la operación. La instalación original y los datos existentes se conservan.'


def import_installation(source, destination):
    # Local provenance for an explicit subsequent connection transfer. No keys
    # are retrieved and no Desktop shortcut is changed during the import.
    return import_legacy(source, destination, platform='linux', record_source=True)


def prepare(resources, root):
    import gi
    gi.require_version('Gtk', '3.0')
    from gi.repository import Gtk

    dialog = Gtk.Dialog(title='Bienvenido a Codex Model Router')
    dialog.set_default_size(520, 180)
    dialog.add_button('Cancelar', Gtk.ResponseType.CANCEL)
    dialog.add_button('Empezar de cero', 1)
    dialog.add_button('Importar instalación…', 2)
    label = Gtk.Label(label='Conserva tus ajustes, historial y referencias a las claves.\n'
                      'Para importar, termina las tareas y cierra Codex y el monitor anterior.\n'
                      'La carpeta original se conservará como respaldo.')
    label.set_margin_start(20); label.set_margin_end(20)
    label.set_margin_top(20); label.set_margin_bottom(20)
    dialog.get_content_area().add(label)
    dialog.show_all()
    try:
        while True:
            response = dialog.run()
            if response not in (1, 2):
                return False
            try:
                if response == 1:
                    bootstrap(resources, root, platform='linux')
                else:
                    chooser = Gtk.FileChooserDialog(title='Carpeta de la instalación anterior',
                        transient_for=dialog, action=Gtk.FileChooserAction.SELECT_FOLDER)
                    chooser.add_buttons('Cancelar', Gtk.ResponseType.CANCEL, 'Importar', Gtk.ResponseType.OK)
                    try:
                        if chooser.run() != Gtk.ResponseType.OK:
                            continue
                        source = chooser.get_filename()
                    finally:
                        chooser.destroy()
                    import_installation(source, root)
                return True
            except (OSError, ValueError, TimeoutError) as error:
                message = Gtk.MessageDialog(transient_for=dialog, modal=True,
                    message_type=Gtk.MessageType.WARNING, buttons=Gtk.ButtonsType.OK,
                    text='No se pudo preparar la instalación.')
                message.format_secondary_text(error_detail(error))
                message.run(); message.destroy()
    finally:
        dialog.destroy()
