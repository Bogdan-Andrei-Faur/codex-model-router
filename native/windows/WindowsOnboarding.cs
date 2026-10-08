// First-run UI, independent of WebView2. Import never changes Desktop.
using System;
using System.Collections.Generic;
using System.IO;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using Forms=System.Windows.Forms;

static class WindowsOnboarding
{
    internal static string FailureMessage(string result)
    {
        // Only fixed error codes cross into the UI; never show raw runtime output.
        try {
            var response=WindowsLayout.Json.Deserialize<Dictionary<string,object>>(result);
            var error=(Dictionary<string,object>)response["error"];
            switch((string)error["code"]) {
                case "busy_source":return "El monitor anterior o una escritura de datos sigue activo. Cierra el monitor anterior por completo y vuelve a importar. Tus datos se conservan.";
                case "active_bridge":return "Codex sigue usando la instalación anterior. Termina las tareas y cierra Codex antes de importar. Tus datos se conservan.";
                case "missing_config":return "Esta carpeta no contiene config.local.json. Selecciona la raíz de la instalación anterior, no la carpeta state.";
                case "invalid_config":return "config.local.json no contiene una configuración JSON válida. Tus datos se conservan.";
                case "foreign_platform":return "La configuración pertenece a otro sistema. Selecciona la instalación de este ordenador.";
                case "occupied_destination":return "La instalación nueva ya contiene datos. No se puede importar encima; tus datos se conservan.";
                case "unreadable_status":return "No se puede comprobar el estado de la instalación anterior. Tus datos se conservan.";
            }
        } catch { }
        return "No se pudo preparar la instalación. Comprueba el acceso a la carpeta y vuelve a intentarlo. Tus datos se conservan.";
    }
    internal static bool Prepare(string resources,string root)
    {
        if(File.Exists(Path.Combine(root,"config.local.json")))return true;
        var dialog=new Window {Title="Codex Model Router",Width=550,SizeToContent=SizeToContent.Height,ResizeMode=ResizeMode.NoResize,
            WindowStartupLocation=WindowStartupLocation.CenterScreen,Background=new SolidColorBrush(Color.FromRgb(36,37,44)),Foreground=Brushes.White};
        var panel=new StackPanel {Margin=new Thickness(24)};dialog.Content=panel;
        var title=new TextBlock {Text="Bienvenido a Codex Model Router",FontSize=20,Margin=new Thickness(0,0,0,14)};panel.Children.Add(title);
        var description=new TextBlock {Text="Puedes empezar de cero o importar tus ajustes, claves e historial.\nPara importar, termina las tareas y cierra Codex y el monitor anterior. La carpeta original se conserva.",TextWrapping=TextWrapping.Wrap,FontSize=13};panel.Children.Add(description);
        var feedback=new TextBlock {TextWrapping=TextWrapping.Wrap,Margin=new Thickness(0,12,0,10),Foreground=Brushes.LightSalmon};panel.Children.Add(feedback);
        var buttons=new WrapPanel();panel.Children.Add(buttons);bool prepared=false;
        Action<string,string> operation=delegate(string service,string arguments){
            try {
                string result;
                if(WindowsLayout.Run(resources,root,service,arguments,out result)!=0){feedback.Text=FailureMessage(result);return;}
                title.Text=service=="import-legacy"?"Importación completada":"Instalación preparada";
                description.Text=service=="import-legacy"
                    ?"Tus ajustes, claves e historial disponibles se han importado correctamente. La carpeta original se conserva."
                    :"Tu configuración inicial se ha creado correctamente.";
                feedback.Foreground=new SolidColorBrush(Color.FromRgb(151,222,183));
                feedback.Text="Siguiente paso: abre el monitor y conecta Codex desde Ajustes. Después podrás reiniciar Codex cuando termines tus tareas.";
                buttons.Children.Clear();
                var open=ActionButton("Abrir monitor");open.IsDefault=true;
                open.Click+=delegate {prepared=true;dialog.Close();};buttons.Children.Add(open);
                var close=ActionButton("Cerrar");close.IsCancel=true;
                close.Click+=delegate {dialog.Close();};buttons.Children.Add(close);
                open.Focus();
            }
            catch{feedback.Text=FailureMessage("");}
        };
        foreach(string name in new[]{"Empezar de cero","Importar instalación…","Cancelar"}) {
            var button=ActionButton(name);
            button.Click+=delegate {
                if(name=="Cancelar"){dialog.Close();return;}
                if(name=="Empezar de cero"){operation("bootstrap","");return;}
                using(var chooser=new Forms.FolderBrowserDialog {Description="Carpeta de la instalación anterior",ShowNewFolderButton=false})
                    if(chooser.ShowDialog()==Forms.DialogResult.OK)operation("import-legacy",WindowsLayout.Quote(chooser.SelectedPath));
            };
            buttons.Children.Add(button);
        }
        dialog.ShowDialog();return prepared;
    }
    static Button ActionButton(string name)
    {
        var button=new Button {Content=name,Padding=new Thickness(12,7,12,7),Margin=new Thickness(0,0,8,0),Background=new SolidColorBrush(Color.FromRgb(55,54,68)),Foreground=Brushes.White,BorderThickness=new Thickness(0)};
        var template=new ControlTemplate(typeof(Button));var border=new FrameworkElementFactory(typeof(Border));border.SetValue(Border.CornerRadiusProperty,new CornerRadius(16));border.SetValue(Border.BackgroundProperty,new System.Windows.TemplateBindingExtension(Button.BackgroundProperty));var content=new FrameworkElementFactory(typeof(ContentPresenter));content.SetValue(ContentPresenter.MarginProperty,new System.Windows.TemplateBindingExtension(Button.PaddingProperty));border.AppendChild(content);template.VisualTree=border;button.Template=template;
        return button;
    }
}
