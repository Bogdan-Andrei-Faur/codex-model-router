using System;
using System.IO;
using System.Linq;
using System.Collections;
using System.Collections.Generic;
using System.Diagnostics;
using System.Threading;
using System.Runtime.InteropServices;
using System.Web.Script.Serialization;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Controls.Primitives;
using System.Windows.Input;
using System.Windows.Media;
using System.Windows.Media.Animation;
using System.Windows.Media.Effects;
using System.Windows.Media.Imaging;
using System.Windows.Threading;
using Forms = System.Windows.Forms;
using Drawing = System.Drawing;

internal enum MonitorMode { Hidden, Compact, Expanded }

internal sealed partial class ModernRouterMonitor : Window
{
    const string WindowTitle = "Codex automático · Monitor";
    static readonly string Root = Path.GetFullPath(Path.Combine(AppDomain.CurrentDomain.BaseDirectory, ".."));
    static readonly string ProductVersion = ReadProductVersion();
    static readonly string ProductBuildId = ReadProductBuildId();
    static readonly string RouterBuildId = ReadProductBuildId(2);
    static readonly string StateFolder = Path.Combine(Root, "state");
    static readonly string RestartRequiredPath = Path.Combine(StateFolder, "restart-required.json");
    static readonly string UiStatePath = Path.Combine(StateFolder, "monitor-ui.json");
    static readonly JavaScriptSerializer Json = new JavaScriptSerializer { MaxJsonLength = 8 * 1024 * 1024 };

    static readonly Brush Panel = Brush("#FF24252B"), Panel2 = Brush("#FF30313A"), Ink = Brush("#FFF3F3F5");
    static readonly Brush Muted = Brush("#FFADAEB9"), Line = Brush("#FF44454E"), Accent = Brush("#FFC7BBFF");
    static readonly Brush Good = Brush("#FF93D2AD"), Warning = Brush("#FFDFC17B"), TransparentBrush = Brushes.Transparent;

    readonly bool preview;
    readonly Border shell = new Border();
    readonly Grid surface = new Grid { Margin = new Thickness(8), VerticalAlignment = VerticalAlignment.Bottom, HorizontalAlignment = HorizontalAlignment.Right };
    readonly Grid compactView = new Grid(), expandedView = new Grid();
    readonly StackPanel taskList = new StackPanel();
    readonly ScrollViewer activityScroll = new ScrollViewer { VerticalScrollBarVisibility = ScrollBarVisibility.Auto,
        HorizontalScrollBarVisibility = ScrollBarVisibility.Disabled, PanningMode = PanningMode.VerticalOnly };
    readonly StackPanel mainTags = new StackPanel { Orientation = Orientation.Horizontal };
    readonly Grid headerActivity = new Grid { Width = 18, Height = 18 };
    readonly TextBlock compactCount = Txt("0 activas", 12, Muted, FontWeights.Medium);
    readonly TextBlock connection = Txt("Esperando conexión", 12, Muted);
    readonly TextBlock mainTask = Txt("Sin tarea seleccionada", 17, Ink, FontWeights.SemiBold);
    readonly Border taskModeHost = new Border();
    string taskModeSignature;
    string featuredSelection;
    DateTime featuredUntil;
    Button featuredRelease;
    readonly TextBlock confirmation = Txt("Sin confirmación", 12, Muted);
    readonly TextBlock reason = Txt("Todavía no hay una decisión del selector.", 13, Muted);
    readonly TextBlock effortReason = Txt("Todavía no hay una decisión de razonamiento.", 13, Muted);
    readonly Border reasonBox = new Border();
    readonly Button pauseButton;
    readonly DispatcherTimer timer = new DispatcherTimer();
    readonly Forms.NotifyIcon tray = new Forms.NotifyIcon();
    ContextMenu trayMenu;
    MenuItem trayCompact, trayExpanded, trayHidden, trayPause, trayTopmost;
    MonitorMode mode = MonitorMode.Compact;
    bool quitting, reasonOpen;
    readonly Dictionary<string, double> panelHeights = new Dictionary<string, double>();
    readonly Thumb heightGrip = new Thumb();
    double resizeStartY, resizeStartHeight;
    Forms.Screen resizeScreen;
    string activitySignature;
    int lastActiveCount = -1;
    bool lastConnected;
    readonly Dictionary<string, double> telemetryHealth = new Dictionary<string, double>();
    bool telemetryReceiverAvailable;
    internal static readonly TimeSpan ModeTransitionDuration = TimeSpan.FromMilliseconds(420);

    public ModernRouterMonitor(bool isPreview)
    {
        preview = isPreview;
        Title = WindowTitle + " · v" + ProductVersion;
        WindowStyle = WindowStyle.None;
        AllowsTransparency = true;
        Background = Brushes.Transparent;
        ShowInTaskbar = false;
        ResizeMode = ResizeMode.NoResize;
        ShowActivated = false;
        Topmost = true;
        FontFamily = new FontFamily("Segoe UI");
        TextOptions.SetTextFormattingMode(this, TextFormattingMode.Display);
        TextOptions.SetTextRenderingMode(this, TextRenderingMode.Grayscale);
        SnapsToDevicePixels = true;
        UseLayoutRounding = true;
        Resources[typeof(ScrollBar)] = System.Windows.Markup.XamlReader.Parse(@"
<Style xmlns='http://schemas.microsoft.com/winfx/2006/xaml/presentation'
       xmlns:x='http://schemas.microsoft.com/winfx/2006/xaml' TargetType='{x:Type ScrollBar}'>
 <Setter Property='Width' Value='10'/><Setter Property='Background' Value='Transparent'/>
 <Setter Property='Template'><Setter.Value><ControlTemplate TargetType='{x:Type ScrollBar}'>
  <Grid Background='Transparent' Margin='2,5'>
   <Track x:Name='PART_Track' Orientation='Vertical' IsDirectionReversed='True'
          Minimum='{TemplateBinding Minimum}' Maximum='{TemplateBinding Maximum}'
          Value='{Binding Value, RelativeSource={RelativeSource TemplatedParent}, Mode=TwoWay}'
          ViewportSize='{TemplateBinding ViewportSize}'>
    <Track.DecreaseRepeatButton><RepeatButton Command='{x:Static ScrollBar.PageUpCommand}' Focusable='False'>
     <RepeatButton.Template><ControlTemplate><Border Background='Transparent'/></ControlTemplate></RepeatButton.Template>
    </RepeatButton></Track.DecreaseRepeatButton>
    <Track.Thumb><Thumb MinHeight='24'><Thumb.Template><ControlTemplate TargetType='{x:Type Thumb}'>
     <Border x:Name='grip' Background='#626472' CornerRadius='3'/>
     <ControlTemplate.Triggers><Trigger Property='IsMouseOver' Value='True'>
      <Setter TargetName='grip' Property='Background' Value='#A49ABF'/>
     </Trigger></ControlTemplate.Triggers>
    </ControlTemplate></Thumb.Template></Thumb></Track.Thumb>
    <Track.IncreaseRepeatButton><RepeatButton Command='{x:Static ScrollBar.PageDownCommand}' Focusable='False'>
     <RepeatButton.Template><ControlTemplate><Border Background='Transparent'/></ControlTemplate></RepeatButton.Template>
    </RepeatButton></Track.IncreaseRepeatButton>
   </Track>
  </Grid>
 </ControlTemplate></Setter.Value></Setter>
</Style>");
        var iconPath = Path.Combine(Root, "assets", "codex.ico");
        var windowIconPath = Path.Combine(Root, "assets", "codex-official.png");
        if (File.Exists(windowIconPath)) Icon = new BitmapImage(new Uri(windowIconPath));

        shell.Background = Panel;
        shell.BorderBrush = Line;
        shell.BorderThickness = new Thickness(1);
        shell.CornerRadius = new CornerRadius(26);
        // Keep the shadow outside the content render tree so it cannot rasterize text.
        RenderOptions.SetClearTypeHint(shell, ClearTypeHint.Enabled);
        var content = new Grid();
        content.Children.Add(compactView);
        content.Children.Add(expandedView);
        shell.Child = content;
        shell.ClipToBounds = true;
        surface.Children.Add(new Border { Background = Panel, CornerRadius = shell.CornerRadius,
            Effect = new DropShadowEffect { Color = Colors.Black, Opacity = .34, BlurRadius = 15, ShadowDepth = 2 } });
        surface.Children.Add(shell);
        heightGrip.Height = 14;
        heightGrip.Margin = new Thickness(32, 0, 32, 0);
        heightGrip.VerticalAlignment = VerticalAlignment.Top;
        heightGrip.Cursor = Cursors.SizeNS;
        heightGrip.Focusable = true;
        heightGrip.ToolTip = "Arrastra para ajustar la altura. Doble clic para altura automática.";
        System.Windows.Automation.AutomationProperties.SetName(heightGrip, "Ajustar altura del panel");
        heightGrip.Template = (ControlTemplate)System.Windows.Markup.XamlReader.Parse(@"
<ControlTemplate xmlns='http://schemas.microsoft.com/winfx/2006/xaml/presentation' TargetType='Thumb'>
 <Grid Background='Transparent'><Border Width='38' Height='3' VerticalAlignment='Top' Margin='0,5,0,0' Background='#626472' CornerRadius='2'/></Grid>
</ControlTemplate>");
        heightGrip.DragStarted += delegate {
            resizeScreen = CurrentScreen();
            resizeStartY = Forms.Cursor.Position.Y;
            resizeStartHeight = surface.ActualHeight + 16;
            surface.BeginAnimation(FrameworkElement.HeightProperty, null);
        };
        heightGrip.DragDelta += delegate {
            SetPanelHeight(resizeScreen, resizeStartHeight + (resizeStartY - Forms.Cursor.Position.Y) / (SystemDpi() / 96.0));
        };
        heightGrip.DragCompleted += delegate { SaveUiState(); resizeScreen = null; };
        heightGrip.MouseDoubleClick += delegate { panelHeights.Remove(CurrentScreen().DeviceName); ApplyPanelHeight(); SaveUiState(); };
        heightGrip.KeyDown += delegate(object sender, KeyEventArgs e) {
            if (e.Key != Key.Up && e.Key != Key.Down && e.Key != Key.Home) return;
            var screen = CurrentScreen();
            if (e.Key == Key.Home) { panelHeights.Remove(screen.DeviceName); ApplyPanelHeight(); }
            else SetPanelHeight(screen, surface.ActualHeight + 16 + (e.Key == Key.Up ? 24 : -24));
            SaveUiState(); e.Handled = true;
        };
        surface.Children.Add(heightGrip);
        Content = surface;

        BuildCompact();
        pauseButton = Btn("Ⅱ  Pausar selección", delegate { TogglePause(); }, false);
        BuildExpanded();
        Closing += OnClosing;
        if (!preview)
        {
            Microsoft.Win32.SystemEvents.DisplaySettingsChanged += DisplayChanged;
            SystemParameters.StaticPropertyChanged += WorkAreaChanged;
        }

        Directory.CreateDirectory(StateFolder);
        LoadUiState();
        BuildTray(iconPath);
        timer.Interval = TimeSpan.FromSeconds(2);
        timer.Tick += delegate { RefreshData(); };
        if (!preview) timer.Start();
        RefreshData();
    }

    static SolidColorBrush Brush(string value)
    {
        var brush = new SolidColorBrush((Color)ColorConverter.ConvertFromString(value));
        brush.Freeze(); return brush;
    }

    static TextBlock Txt(string text, double size, Brush foreground, FontWeight? weight = null)
    {
        return new TextBlock { Text = text, FontSize = size, Foreground = foreground,
            FontWeight = weight ?? FontWeights.Normal, TextTrimming = TextTrimming.CharacterEllipsis,
            TextWrapping = TextWrapping.NoWrap, VerticalAlignment = VerticalAlignment.Center };
    }

    static ControlTemplate ButtonTemplate()
    {
        var border = new FrameworkElementFactory(typeof(Border));
        border.SetValue(Border.CornerRadiusProperty, new CornerRadius(17));
        border.SetBinding(Border.BackgroundProperty, new System.Windows.Data.Binding("Background") { RelativeSource = new System.Windows.Data.RelativeSource(System.Windows.Data.RelativeSourceMode.TemplatedParent) });
        border.SetBinding(Border.BorderBrushProperty, new System.Windows.Data.Binding("BorderBrush") { RelativeSource = new System.Windows.Data.RelativeSource(System.Windows.Data.RelativeSourceMode.TemplatedParent) });
        border.SetBinding(Border.BorderThicknessProperty, new System.Windows.Data.Binding("BorderThickness") { RelativeSource = new System.Windows.Data.RelativeSource(System.Windows.Data.RelativeSourceMode.TemplatedParent) });
        border.SetBinding(Border.PaddingProperty, new System.Windows.Data.Binding("Padding") { RelativeSource = new System.Windows.Data.RelativeSource(System.Windows.Data.RelativeSourceMode.TemplatedParent) });
        var presenter = new FrameworkElementFactory(typeof(ContentPresenter));
        presenter.SetValue(ContentPresenter.HorizontalAlignmentProperty, HorizontalAlignment.Center);
        presenter.SetValue(ContentPresenter.VerticalAlignmentProperty, VerticalAlignment.Center);
        border.AppendChild(presenter);
        var template = new ControlTemplate(typeof(Button)) { VisualTree = border };
        var hover = new Trigger { Property = Button.IsMouseOverProperty, Value = true };
        hover.Setters.Add(new Setter(Button.BackgroundProperty, Panel2));
        template.Triggers.Add(hover);
        var focus = new Trigger { Property = Button.IsKeyboardFocusedProperty, Value = true };
        focus.Setters.Add(new Setter(Button.BackgroundProperty, Panel2));
        focus.Setters.Add(new Setter(Button.BorderBrushProperty, Accent));
        focus.Setters.Add(new Setter(Button.BorderThicknessProperty, new Thickness(1)));
        template.Triggers.Add(focus);
        return template;
    }

    static Button Btn(string text, RoutedEventHandler click, bool icon)
    {
        var button = new Button { Content = text, Height = 34, MinWidth = icon ? 34 : 80,
            Padding = icon ? new Thickness(5) : new Thickness(10, 4, 10, 4), Foreground = icon ? Muted : Ink,
            Background = TransparentBrush, BorderBrush = TransparentBrush, BorderThickness = new Thickness(0),
            Template = ButtonTemplate(), Cursor = Cursors.Hand, FontSize = icon ? 20 : 12,
            FontWeight = FontWeights.Medium };
        button.Click += click; return button;
    }

    Image Logo(double size)
    {
        var image = new Image { Width = size, Height = size, Stretch = Stretch.Uniform };
        var path = Path.Combine(Root, "assets", "codex-ui-1024.png");
        if (!File.Exists(path)) path = Path.Combine(Root, "assets", "codex-official.png");
        if (File.Exists(path)) image.Source = new BitmapImage(new Uri(path));
        RenderOptions.SetBitmapScalingMode(image, BitmapScalingMode.HighQuality);
        return image;
    }

    static FrameworkElement NavigationGlyph(string path, double width)
    {
        return new System.Windows.Shapes.Path {
            Data = System.Windows.Media.Geometry.Parse(path), Stroke = Muted,
            StrokeThickness = 1.6, StrokeStartLineCap = PenLineCap.Round,
            StrokeEndLineCap = PenLineCap.Round, StrokeLineJoin = PenLineJoin.Round,
            Width = width, Height = 10, Stretch = Stretch.Uniform,
            HorizontalAlignment = HorizontalAlignment.Center, VerticalAlignment = VerticalAlignment.Center
        };
    }

    void BuildCompact() { BuildAgentCapsule(); }

    void BuildExpanded()
    {
        expandedView.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
        expandedView.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
        expandedView.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
        expandedView.RowDefinitions.Add(new RowDefinition { Height = new GridLength(1) });
        expandedView.RowDefinitions.Add(new RowDefinition { Height = new GridLength(1, GridUnitType.Star) });
        expandedView.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });

        var header = new Grid { Margin = new Thickness(18, 16, 12, 11) };
        header.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(40) });
        header.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
        header.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(36) });
        header.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(36) });
        var logo = Logo(32); Grid.SetColumn(logo, 0); header.Children.Add(logo);
        var headerCopy = new StackPanel { VerticalAlignment = VerticalAlignment.Center };
        headerCopy.Children.Add(Txt("Codex automático", 14, Ink, FontWeights.SemiBold));
        var connectionRow = new StackPanel { Orientation = Orientation.Horizontal };
        connectionRow.Children.Add(headerActivity); connectionRow.Children.Add(connection);
        headerCopy.Children.Add(connectionRow); Grid.SetColumn(headerCopy, 1); header.Children.Add(headerCopy);
        var collapse = Btn("›", delegate { SwitchMode(MonitorMode.Compact, true); }, true);
        collapse.ToolTip = "Volver a vista compacta"; Grid.SetColumn(collapse, 2); header.Children.Add(collapse);
        collapse.Content = NavigationGlyph("M0,0 L5,5 L0,10", 6);
        collapse.VerticalAlignment = VerticalAlignment.Center;
        System.Windows.Automation.AutomationProperties.SetName(collapse, "Volver a vista compacta");
        var hide = Btn("×", delegate { SwitchMode(MonitorMode.Hidden, true); }, true);
        hide.ToolTip = "Ocultar monitor"; Grid.SetColumn(hide, 3); header.Children.Add(hide);
        hide.Content = NavigationGlyph("M0,0 L10,10 M10,0 L0,10", 10);
        hide.VerticalAlignment = VerticalAlignment.Center;
        System.Windows.Automation.AutomationProperties.SetName(hide, "Ocultar monitor");
        Grid.SetRow(header, 0); expandedView.Children.Add(header);

        var tabs = BuildTabBar(); Grid.SetRow(tabs, 1); expandedView.Children.Add(tabs);

        var main = new StackPanel { Margin = new Thickness(18, 7, 18, 17) };
        main.Children.Add(Label("TAREA DESTACADA"));
        featuredRelease = Btn("Fijada 1 min · Volver al más reciente", delegate {
            featuredSelection = null; RefreshData();
        }, false);
        featuredRelease.Foreground = Accent; featuredRelease.FontSize = 11;
        featuredRelease.HorizontalAlignment = HorizontalAlignment.Left;
        featuredRelease.Visibility = Visibility.Collapsed;
        main.Children.Add(featuredRelease);
        var featuredRow = new Grid { Margin = new Thickness(0, 9, 0, 0) };
        featuredRow.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(56) });
        featuredRow.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
        featuredAgentHost.HorizontalAlignment = HorizontalAlignment.Left; featuredAgentHost.VerticalAlignment = VerticalAlignment.Center;
        featuredRow.Children.Add(featuredAgentHost);
        var featuredCopy = new StackPanel();
        mainTask.Margin = new Thickness(0, 0, 0, 8); featuredCopy.Children.Add(mainTask);
        mainTask.ToolTip = mainTask.Text;
        featuredCopy.Children.Add(mainTags); Grid.SetColumn(featuredCopy, 1); featuredRow.Children.Add(featuredCopy);
        main.Children.Add(featuredRow);
        var featuredHistory = Btn("Ver historial", delegate {
            if (featuredAvatar != null) OpenHistoryForThread(featuredAvatar.Id);
        }, false);
        featuredHistory.Foreground = Accent; featuredHistory.HorizontalAlignment = HorizontalAlignment.Left;
        main.Children.Add(featuredHistory);
        main.Children.Add(taskModeHost);
        confirmation.Margin = new Thickness(0, 9, 0, 0); main.Children.Add(confirmation);
        var why = Btn("¿Por qué esta elección?", delegate
        {
            reasonOpen = !reasonOpen; reasonBox.Visibility = reasonOpen ? Visibility.Visible : Visibility.Collapsed;
        }, false);
        why.Foreground = Accent; why.HorizontalAlignment = HorizontalAlignment.Left; why.Margin = new Thickness(-10, 7, 0, 0);
        main.Children.Add(why);
        reason.TextWrapping = TextWrapping.Wrap; effortReason.TextWrapping = TextWrapping.Wrap;
        reasonBox.Margin = new Thickness(2, 4, 0, 0); reasonBox.Padding = new Thickness(10, 3, 0, 3);
        reasonBox.BorderBrush = Accent; reasonBox.BorderThickness = new Thickness(2, 0, 0, 0);
        var reasonStack = new StackPanel(); reasonStack.Children.Add(Label("POR QUÉ EL MODELO"));
        reason.Margin = new Thickness(0, 4, 0, 10); reasonStack.Children.Add(reason);
        reasonStack.Children.Add(Label("POR QUÉ EL RAZONAMIENTO"));
        effortReason.Margin = new Thickness(0, 4, 0, 0); reasonStack.Children.Add(effortReason);
        reasonBox.Child = reasonStack; reasonBox.Visibility = Visibility.Collapsed; main.Children.Add(reasonBox);
        main.Children.Add(phaseHost);
        var mainScroll = new ScrollViewer { Content = main, VerticalScrollBarVisibility = ScrollBarVisibility.Auto,
            HorizontalScrollBarVisibility = ScrollBarVisibility.Disabled };
        surface.SizeChanged += delegate { mainScroll.MaxHeight = Math.Max(140, surface.ActualHeight * .62); };
        Grid.SetRow(mainScroll, 2); expandedView.Children.Add(mainScroll);

        var separator = new Border { Background = Line, Height = 1, Margin = new Thickness(18, 0, 18, 0) };
        Grid.SetRow(separator, 3); expandedView.Children.Add(separator);
        activityScroll.Content = taskList; Grid.SetRow(activityScroll, 4); expandedView.Children.Add(activityScroll);
        RegisterActivityElements(mainScroll, separator, activityScroll);
        foreach (var page in new[] { historyPage, statisticsPage, settingsPage })
        {
            Grid.SetRow(page, 2); Grid.SetRowSpan(page, 3); expandedView.Children.Add(page);
        }

        var footer = new Grid { Margin = new Thickness(10, 8, 10, 10) };
        footer.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });
        footer.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
        footer.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });
        Grid.SetColumn(pauseButton, 0); footer.Children.Add(pauseButton);
        var version = versionLabel;
        version.ToolTip = "Versión de Codex automático";
        Grid.SetColumn(version, 2); footer.Children.Add(version);
        Grid.SetRow(footer, 5); expandedView.Children.Add(footer);
        SelectMonitorTab(0);
    }

    static TextBlock Label(string text)
    {
        return Txt(text, 11, Muted, FontWeights.SemiBold);
    }

    static string ReadProductVersion()
    {
        try
        {
            var info = (System.Reflection.AssemblyInformationalVersionAttribute)Attribute.GetCustomAttribute(
                System.Reflection.Assembly.GetExecutingAssembly(), typeof(System.Reflection.AssemblyInformationalVersionAttribute));
            var value = info != null ? info.InformationalVersion.Split('+')[0] : "sin identificar";
            return value.Length > 0 && value.Length <= 20 ? value : "0.1.0";
        }
        catch { return "0.1.0"; }
    }

    static string ReadProductBuildId(int part = 1)
    {
        var info = (System.Reflection.AssemblyInformationalVersionAttribute)Attribute.GetCustomAttribute(
            System.Reflection.Assembly.GetExecutingAssembly(), typeof(System.Reflection.AssemblyInformationalVersionAttribute));
        return info != null && info.InformationalVersion.Split('+').Length > part ? info.InformationalVersion.Split('+')[part] : "";
    }

    void BuildTray(string iconPath)
    {
        trayMenu = new ContextMenu { Width = 312, Background = Panel, Foreground = Ink,
            FontFamily = FontFamily, FontSize = 13, BorderBrush = Line, BorderThickness = new Thickness(1),
            HasDropShadow = false, Placement = PlacementMode.AbsolutePoint, SnapsToDevicePixels = true,
            UseLayoutRounding = true };
        TextOptions.SetTextFormattingMode(trayMenu, TextFormattingMode.Display);
        TextOptions.SetTextRenderingMode(trayMenu, TextRenderingMode.Grayscale);
        var border = new FrameworkElementFactory(typeof(Border));
        border.SetValue(Border.BackgroundProperty, Panel); border.SetValue(Border.BorderBrushProperty, Line);
        border.SetValue(Border.BorderThicknessProperty, new Thickness(1));
        border.SetValue(Border.CornerRadiusProperty, new CornerRadius(20));
        border.SetValue(Border.PaddingProperty, new Thickness(7));
        var items = new FrameworkElementFactory(typeof(StackPanel));
        items.SetValue(StackPanel.IsItemsHostProperty, true); border.AppendChild(items);
        trayMenu.Template = new ControlTemplate(typeof(ContextMenu)) { VisualTree = border };
        var title = new StackPanel { Margin = new Thickness(12, 9, 12, 10) };
        title.Children.Add(Txt("Codex automático", 14, Ink, FontWeights.SemiBold));
        title.Children.Add(Txt("Tu monitor de actividad", 12, Muted));
        trayMenu.Items.Add(new MenuItem { Header = title, IsEnabled = false, Focusable = false,
            Template = MenuTemplate() });
        trayCompact = MenuEntry("Vista compacta", delegate { SwitchMode(MonitorMode.Compact, true); });
        trayExpanded = MenuEntry("Panel lateral", delegate { SwitchMode(MonitorMode.Expanded, true); });
        trayHidden = MenuEntry("Ocultar monitor", delegate { SwitchMode(MonitorMode.Hidden, true); });
        trayPause = MenuEntry("Pausar selección", delegate { TogglePause(); });
        trayTopmost = MenuEntry("Mantener delante", delegate { Topmost = !Topmost; SaveUiState(); UpdateTray(); });
        trayMenu.Items.Add(MenuSeparator()); trayMenu.Items.Add(trayCompact);
        trayMenu.Items.Add(trayExpanded); trayMenu.Items.Add(trayHidden); trayMenu.Items.Add(MenuSeparator());
        trayMenu.Items.Add(trayPause); trayMenu.Items.Add(trayTopmost); trayMenu.Items.Add(MenuSeparator());
        trayMenu.Items.Add(MenuEntry("Salir del monitor", delegate { quitting = true; Close(); }));
        trayMenu.Opened += delegate { UpdateTray(); };
        UpdateTray();
        if (preview) return;
        tray.Icon = new Drawing.Icon(iconPath); tray.Text = "Codex automático"; tray.Visible = true;
        tray.MouseUp += delegate(object sender, Forms.MouseEventArgs e)
        {
            if (e.Button == Forms.MouseButtons.Right)
            {
                var point = Forms.Cursor.Position;
                Dispatcher.BeginInvoke(new Action(delegate {
                    UpdateTray();
                    double scale = SystemDpi() / 96.0;
                    trayMenu.HorizontalOffset = point.X / scale;
                    trayMenu.VerticalOffset = point.Y / scale;
                    trayMenu.IsOpen = true;
                    trayMenu.Focus();
                }));
                return;
            }
            if (e.Button != Forms.MouseButtons.Left) return;
            Dispatcher.BeginInvoke(new Action(delegate
            {
                SwitchMode(mode == MonitorMode.Hidden ? MonitorMode.Compact : mode == MonitorMode.Compact ? MonitorMode.Expanded : MonitorMode.Compact, true);
            }));
        };
    }

    static ControlTemplate MenuTemplate()
    {
        var border = new FrameworkElementFactory(typeof(Border));
        border.SetValue(Border.CornerRadiusProperty, new CornerRadius(17));
        border.SetBinding(Border.BackgroundProperty, new System.Windows.Data.Binding("Background") {
            RelativeSource = new System.Windows.Data.RelativeSource(System.Windows.Data.RelativeSourceMode.TemplatedParent) });
        var presenter = new FrameworkElementFactory(typeof(ContentPresenter));
        presenter.SetValue(ContentPresenter.ContentSourceProperty, "Header"); border.AppendChild(presenter);
        var template = new ControlTemplate(typeof(MenuItem)) { VisualTree = border };
        var hover = new Trigger { Property = MenuItem.IsHighlightedProperty, Value = true };
        hover.Setters.Add(new Setter(MenuItem.BackgroundProperty, Panel2)); template.Triggers.Add(hover);
        return template;
    }

    static Separator MenuSeparator()
    {
        var border = new FrameworkElementFactory(typeof(Border));
        border.SetValue(Border.BackgroundProperty, Line); border.SetValue(Border.HeightProperty, 1.0);
        return new Separator { Margin = new Thickness(12, 6, 12, 6),
            Template = new ControlTemplate(typeof(Separator)) { VisualTree = border } };
    }

    static MenuItem MenuEntry(string label, Action action)
    {
        var item = new MenuItem { Background = TransparentBrush, Template = MenuTemplate(), MinHeight = 39 };
        SetMenuLabel(item, label, "", false);
        item.Click += delegate { action(); }; return item;
    }

    static void SetMenuLabel(MenuItem item, string label, string state, bool selected)
    {
        var row = new Grid { Margin = new Thickness(12, 10, 12, 10) };
        row.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
        row.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });
        row.Children.Add(Txt(label, 13, Ink, FontWeights.Medium));
        var value = Txt(state == "" && selected ? "✓" : state, 12, selected ? Accent : Muted, FontWeights.SemiBold);
        Grid.SetColumn(value, 1); row.Children.Add(value); item.Header = row;
        item.IsChecked = selected;
        System.Windows.Automation.AutomationProperties.SetName(item, label + (state == "" ? "" : ", " + state));
    }

    void UpdateTray()
    {
        if (trayCompact == null) return;
        SetMenuLabel(trayCompact, "Vista compacta", "", mode == MonitorMode.Compact);
        SetMenuLabel(trayExpanded, "Panel lateral", "", mode == MonitorMode.Expanded);
        SetMenuLabel(trayHidden, "Ocultar monitor", "", mode == MonitorMode.Hidden);
        SetMenuLabel(trayTopmost, "Mantener delante", Topmost ? "Activado" : "Desactivado", Topmost);
        bool enabled = ReadEnabled();
        SetMenuLabel(trayPause, enabled ? "Pausar selección" : "Activar selección", enabled ? "" : "Pausada", !enabled);
    }

    public void Reveal()
    {
        SwitchMode(mode == MonitorMode.Hidden ? MonitorMode.Compact : mode, true);
    }

    public void SwitchMode(MonitorMode target, bool animate)
    {
        mode = target; peekCloseTimer.Stop(); peekAgentId = null; peekSignature = null;
        agentPeek.Visibility = Visibility.Collapsed;
        foreach (var visual in agentAvatars.Values) SetAgentOrbit(visual, false);
        if (target == MonitorMode.Hidden)
        {
            surface.BeginAnimation(FrameworkElement.HeightProperty, null);
            surface.BeginAnimation(FrameworkElement.WidthProperty, null);
            Hide(); SaveUiState(); UpdateTray(); return;
        }
        compactView.Visibility = target == MonitorMode.Compact ? Visibility.Visible : Visibility.Collapsed;
        expandedView.Visibility = target == MonitorMode.Expanded ? Visibility.Visible : Visibility.Collapsed;
        heightGrip.Visibility = target == MonitorMode.Expanded ? Visibility.Visible : Visibility.Collapsed;
        shell.CornerRadius = new CornerRadius(26);
        // Keep the transparent native window fixed. Only the bottom-aligned surface grows;
        // resizing and moving an HWND on separate frames causes lower-edge judder.
        var envelope = Geometry(MonitorMode.Expanded, ScreenWork(CurrentScreen()), 1);
        var geometry = TargetGeometry(target);
        double from = surface.ActualHeight, to = Math.Max(1, geometry.Height - 16);
        double fromWidth = surface.ActualWidth, toWidth = Math.Max(1, geometry.Width - 16);
        Width = envelope.Width; Height = envelope.Height; Left = envelope.Left; Top = envelope.Top;
        surface.BeginAnimation(FrameworkElement.HeightProperty, null);
        surface.Height = to;
        surface.BeginAnimation(FrameworkElement.WidthProperty, null); surface.Width = toWidth;
        if (animate && IsVisible && SystemParameters.ClientAreaAnimation)
        {
            var motion = new DoubleAnimation(from, to, ModeTransitionDuration)
            { EasingFunction = new CubicEase { EasingMode = EasingMode.EaseInOut }, FillBehavior = FillBehavior.Stop };
            surface.BeginAnimation(FrameworkElement.HeightProperty, motion, HandoffBehavior.SnapshotAndReplace);
            surface.BeginAnimation(FrameworkElement.WidthProperty, new DoubleAnimation(fromWidth, toWidth, ModeTransitionDuration)
            { EasingFunction = new CubicEase { EasingMode = EasingMode.EaseInOut }, FillBehavior = FillBehavior.Stop });
        }
        Opacity = 1;
        if (!IsVisible) Show();
        foreach (var visual in agentAvatars.Values) SetAgentOrbit(visual, target == MonitorMode.Compact);
        SaveUiState(); UpdateTray();
    }

    Rect TargetGeometry(MonitorMode target)
    {
        var screen = CurrentScreen();
        double ratio;
        if (!panelHeights.TryGetValue(screen.DeviceName, out ratio)) ratio = .9;
        return Geometry(target, ScreenWork(screen), ratio);
    }

    Forms.Screen CurrentScreen()
    {
        return IsVisible && PresentationSource.FromVisual(this) != null
            ? Forms.Screen.FromHandle(new System.Windows.Interop.WindowInteropHelper(this).Handle)
            : Forms.Screen.FromPoint(Forms.Cursor.Position);
    }

    static Rect ScreenWork(Forms.Screen screen)
    {
        // WinForms coordinates and WPF use the process's system-DPI coordinate space.
        var work = screen.WorkingArea;
        double scale = SystemDpi() / 96.0;
        return new Rect(work.Left / scale, work.Top / scale, work.Width / scale, work.Height / scale);
    }

    void SetPanelHeight(Forms.Screen screen, double height)
    {
        if (screen == null) return;
        var work = ScreenWork(screen);
        panelHeights[screen.DeviceName] = Geometry(MonitorMode.Expanded, work, height / work.Height).Height / work.Height;
        ApplyPanelHeight();
    }

    void ApplyPanelHeight()
    {
        surface.BeginAnimation(FrameworkElement.HeightProperty, null);
        surface.Height = Math.Max(1, TargetGeometry(MonitorMode.Expanded).Height - 16);
    }

    internal static Rect Geometry(MonitorMode target, Rect work, double ratio = .9)
    {
        const double margin = 10; // The surface has an additional 8 DIP shadow inset.
        double width = Math.Min(target == MonitorMode.Compact ? 382 : 432, Math.Max(1, work.Width - margin * 2));
        if (Double.IsNaN(ratio) || Double.IsInfinity(ratio) || ratio <= 0) ratio = .9;
        double height = Math.Min(target == MonitorMode.Compact ? 96 : Math.Max(560, work.Height * ratio), Math.Max(1, work.Height - margin * 2));
        return new Rect(work.Right - width - margin, work.Bottom - height - margin, width, height);
    }

    [DllImport("user32.dll")] static extern uint GetDpiForSystem();
    static double SystemDpi() { try { return GetDpiForSystem(); } catch { return 96; } }

    void DisplayChanged(object sender, EventArgs e)
    {
        Dispatcher.BeginInvoke(new Action(delegate { if (IsVisible) SwitchMode(mode, false); }));
    }

    void WorkAreaChanged(object sender, System.ComponentModel.PropertyChangedEventArgs e)
    {
        if (e.PropertyName == "WorkArea") DisplayChanged(sender, e);
    }

    void TogglePause()
    {
        try
        {
            var path = Path.Combine(Root, "config.local.json");
            var data = Json.Deserialize<Dictionary<string, object>>(File.ReadAllText(path));
            data["enabled"] = !Convert.ToBoolean(data["enabled"]);
            var temp = path + ".monitor.tmp";
            File.WriteAllText(temp, Json.Serialize(data), new System.Text.UTF8Encoding(false));
            File.Replace(temp, path, null);
            RefreshData();
        }
        catch { connection.Text = "No se pudo cambiar la selección"; }
    }

    bool ReadEnabled()
    {
        try { return Convert.ToBoolean(Json.Deserialize<Dictionary<string, object>>(File.ReadAllText(Path.Combine(Root, "config.local.json")))["enabled"]); }
        catch { return true; }
    }

    void RefreshData()
    {
        try
        {
            bool enabled = ReadEnabled();
            pauseButton.Content = enabled ? "Ⅱ  Pausar selección" : "▶  Activar selección";
            var rows = new Dictionary<string, Dictionary<string, object>>();
            var telemetry = new Dictionary<string, double>();
            bool telemetryAvailable = false;
            int connected = 0, modern = 0;
            var bridgeVersions = new HashSet<string>();
            bool bridgeBuildMismatch = false;
            bool bridgeBuildUnknown = false;
            foreach (var file in Directory.GetFiles(StateFolder, "status-*.json").OrderBy(File.GetLastWriteTimeUtc))
            {
                Dictionary<string, object> data;
                try
                {
                    data = Json.Deserialize<Dictionary<string, object>>(File.ReadAllText(file));
                    if (String(data, "client_name") == "other") continue;
                    int pid = Convert.ToInt32(data["pid"]);
                    using (var process = Process.GetProcessById(pid))
                    {
                        if (process.HasExited || !(process.ProcessName.StartsWith("python", StringComparison.OrdinalIgnoreCase) ||
                            process.ProcessName.Equals("codex-router-core", StringComparison.OrdinalIgnoreCase))) continue;
                        // A Windows PID may be reused long after an old snapshot was written.
                        if (process.StartTime.ToUniversalTime() > File.GetLastWriteTimeUtc(file).AddSeconds(5)) continue;
                    }
                    if (data.ContainsKey("heartbeat") && DateTimeOffset.UtcNow.ToUnixTimeSeconds() - Convert.ToDouble(data["heartbeat"]) > 12) continue;
                }
                catch { continue; }
                connected++;
                bridgeVersions.Add(String(data, "product_version", "desconocida"));
                if (RouterBuildId == "" || String(data, "router_build_id") == "") bridgeBuildUnknown = true;
                else if (String(data, "router_build_id") != RouterBuildId) bridgeBuildMismatch = true;
                if (data.ContainsKey("telemetry"))
                {
                    var health = Dict(data["telemetry"]);
                    telemetryAvailable |= String(health, "enabled") == "True" || String(health, "enabled") == "true";
                    foreach (var key in new[] { "requests", "records_scanned", "eligible_records", "events_without_model", "unrecognized_records", "invalid_requests", "unexpected_path",
                        "invalid_size", "invalid_wire_size", "invalid_decoded_size", "invalid_length", "invalid_encoding", "invalid_payload", "invalid_io", "unauthorized_requests", "rejected_connections", "processing_busy",
                        "completion_records", "failure_records", "api_request_records", "stream_records",
                        "size_wire_512k", "size_wire_1m", "size_wire_4m", "size_wire_16m", "size_wire_over16m",
                        "size_decoded_512k", "size_decoded_1m", "size_decoded_4m", "size_decoded_16m", "size_decoded_over16m" })
                        telemetry[key] = telemetry.ContainsKey(key) ? telemetry[key] + Number(health, key) : Number(health, key);
                    var stats = Dict(data.ContainsKey("stats") ? data["stats"] : null);
                    foreach (var key in new[] { "telemetry_events", "telemetry_confirmed", "telemetry_probable", "telemetry_unattributed" })
                        telemetry[key] = telemetry.ContainsKey(key) ? telemetry[key] + Number(stats, key) : Number(stats, key);
                }
                if (data.ContainsKey("threads"))
                {
                    modern++;
                    foreach (var pair in Dict(data["threads"])) rows[pair.Key] = Dict(pair.Value);
                }
                else if (data.ContainsKey("events"))
                {
                    foreach (var value in (IEnumerable)data["events"])
                    {
                        var ev = Dict(value); string id = String(ev, "thread"); if (id == "") continue;
                        Dictionary<string, object> row;
                        if (!rows.TryGetValue(id, out row)) rows[id] = row = new Dictionary<string, object>();
                        foreach (var key in new[] { "model", "effort", "reason" }) if (ev.ContainsKey(key)) row[key] = ev[key];
                        row["name"] = id.Substring(0, Math.Min(8, id.Length)); row["confirmation"] = "Registro anterior";
                        row["status"] = "unknown"; row["updated"] = File.GetLastWriteTimeUtc(file).Ticks;
                    }
                }
            }
            bool restartRequired = File.Exists(RestartRequiredPath);
            versionLabel.Text = "v" + ProductVersion + (bridgeVersions.Any(v => v != ProductVersion) ? " · puente " + System.String.Join(", ", bridgeVersions) : bridgeBuildMismatch ? " · router anterior" : bridgeBuildUnknown ? " · puente sin verificar" : "") +
                (restartRequired ? " · reinicio pendiente" : "");
            versionLabel.Foreground = restartRequired || bridgeBuildMismatch || bridgeVersions.Any(v => v != ProductVersion) ? Warning : Muted;
            versionLabel.ToolTip = "Monitor " + ProductVersion + ". Puentes activos: " + System.String.Join(", ", bridgeVersions) +
                (restartRequired ? ". Hay ajustes pendientes: reinicia Desktop al terminar tus tareas para cargarlos." :
                bridgeBuildMismatch || bridgeVersions.Any(v => v != ProductVersion) ? ". La versión del router activo difiere de la incluida con este monitor. Reinicia Desktop al terminar tus tareas para cargar la versión instalada." : bridgeBuildUnknown ? ". El puente activo no informa su versión de componente. No se puede determinar si necesita reinicio; el próximo inicio de Desktop permitirá comprobarlo." : ".") + " Build del monitor: " + ProductBuildId;
            var ordered = rows.OrderByDescending(x => Active(String(x.Value, "status"))).ThenByDescending(x => Number(x.Value, "updated")).ToList();
            var focus = ChooseFeatured(rows, DateTime.UtcNow);
            int active = ordered.Count(x => Active(String(x.Value, "status")));
            connection.Text = connected == 0 ? "Sin conexión" : modern == 0 ? "Conectado · versión anterior" :
                active + (active == 1 ? " tarea activa" : " tareas activas");
            connection.Foreground = connected == 0 ? Warning : Good;
            UpdateActivitySummary(active, connected > 0);
            if (focus.Key != null) ApplyFocus(focus.Key, focus.Value, active);
            else ApplyEmpty();
            var activityRows = ordered.Where(x => x.Key != focus.Key).ToList();
            var signature = Json.Serialize(activityRows.ToArray());
            if (signature != activitySignature)
            {
                activitySignature = signature;
                taskList.Children.Clear(); taskList.Children.Add(Section("ACTIVIDAD"));
                foreach (var pair in activityRows) taskList.Children.Add(TaskRow(pair.Key, pair.Value));
                if (ordered.Count <= 1) taskList.Children.Add(EmptyRow("No hay otras tareas observables"));
            }
            RefreshAgentCapsule(ordered);
            analyticsConnected = connected > 0;
            telemetryHealth.Clear(); foreach (var pair in telemetry) telemetryHealth[pair.Key] = pair.Value;
            telemetryReceiverAvailable = telemetryAvailable;
            RefreshAnalytics(ordered);
            UpdateTray();
        }
        catch { connection.Text = "Esperando un estado válido"; connection.Foreground = Warning; }
    }

    KeyValuePair<string, Dictionary<string, object>> ChooseFeatured(
        Dictionary<string, Dictionary<string, object>> rows, DateTime now)
    {
        var focus = rows.OrderByDescending(x => Number(x.Value, "updated"))
            .ThenBy(x => x.Key, StringComparer.Ordinal).FirstOrDefault();
        if (featuredSelection != null && now < featuredUntil && rows.ContainsKey(featuredSelection))
            focus = new KeyValuePair<string, Dictionary<string, object>>(featuredSelection, rows[featuredSelection]);
        else featuredSelection = null;
        featuredRelease.Visibility = featuredSelection == null ? Visibility.Collapsed : Visibility.Visible;
        return focus;
    }

    void SelectFeatured(string id)
    {
        featuredSelection = id; featuredUntil = DateTime.UtcNow.AddMinutes(1);
        reasonOpen = false; reasonBox.Visibility = Visibility.Collapsed;
        RefreshData(); activityScroll.ScrollToTop();
    }

    void ApplyFocus(string id, Dictionary<string, object> row, int active)
    {
        string modeSignature = id + ":" + ReadTaskMode(id) + ":" + ReadEnabled();
        if (taskModeSignature != modeSignature)
        {
            taskModeSignature = modeSignature;
            taskModeHost.Child = TaskModeControls(id, delegate { taskModeSignature = null; RefreshData(); });
        }
        string name = String(row, "name", id.Substring(0, Math.Min(8, id.Length)));
        string model = Model(Setting(row, "model", "Sin confirmar"));
        string effort = Effort(Setting(row, "effort", ""));
        FillTags(mainTags, model, effort);
        UpdateFeaturedAgent(id, row);
        RefreshPhasePipeline(id, row);
        mainTask.Text = name; mainTask.ToolTip = name;
        confirmation.Text = String(row, "status") == "pending" ? "Enviando · pendiente de confirmar" : String(row, "confirmation", "Sin confirmar");
        confirmation.Foreground = confirmation.Text == "Aceptado por Codex" ? Good : Muted;
        reason.Text = String(row, "reason", "Observado sin una decisión registrada del selector.");
        effortReason.Text = String(row, "effort_reason", "El registro anterior no separaba el motivo del razonamiento.");
    }

    void ApplyEmpty()
    {
        FillTags(mainTags, "Sin confirmar", "");
        featuredAgentHost.Child = null; featuredAvatar = null;
        mainTask.Text = "Sin tarea seleccionada"; mainTask.ToolTip = mainTask.Text;
        taskModeHost.Child = null; taskModeSignature = null;
        phaseHost.Child = null; phaseSignature = null;
        confirmation.Text = "Sin confirmación"; reason.Text = "Todavía no hay una decisión del selector.";
        effortReason.Text = "Todavía no hay una decisión de razonamiento.";
        confirmation.Foreground = Muted;
    }

    // Pending turns may still carry the previous accepted model in the snapshot.
    static string Setting(Dictionary<string, object> row, string key, string fallback)
    {
        return String(row, "status") == "pending"
            ? String(row, "requested_" + key, fallback)
            : String(row, key, String(row, "requested_" + key, fallback));
    }

    static void FillTags(StackPanel container, string model, string effort)
    {
        if (container.Children.Count == (effort == "" ? 1 : 2) &&
            ((TextBlock)((Border)container.Children[0]).Child).Text == model &&
            (effort == "" || ((TextBlock)((Border)container.Children[1]).Child).Text == effort)) return;
        container.Children.Clear(); container.Children.Add(Badge(model, true));
        if (effort != "")
        {
            var tag = Badge(effort, false); tag.Margin = new Thickness(6, 0, 0, 0); container.Children.Add(tag);
        }
    }

    void UpdateActivitySummary(int active, bool connected)
    {
        if (active == lastActiveCount && connected == lastConnected) return;
        lastActiveCount = active; lastConnected = connected;
        headerActivity.Children.Clear();
        headerActivity.Children.Add(ActivityIndicator(active > 0, connected ? Good : Warning));
        compactCount.Foreground = Muted;
    }

    static Grid ActivityIndicator(bool active, Brush color)
    {
        var indicator = new Grid { Width = 18, Height = 18, VerticalAlignment = VerticalAlignment.Center,
            ToolTip = active ? "Agente trabajando" : "Sin agentes trabajando" };
        var halo = new Border { Width = 10, Height = 10, CornerRadius = new CornerRadius(5),
            Background = color, Opacity = active ? .28 : 0, HorizontalAlignment = HorizontalAlignment.Center,
            VerticalAlignment = VerticalAlignment.Center, RenderTransformOrigin = new Point(.5, .5) };
        var core = new Border { Width = active ? 6 : 5, Height = active ? 6 : 5,
            CornerRadius = new CornerRadius(3), BorderThickness = new Thickness(1), BorderBrush = color,
            Background = active ? color : TransparentBrush, HorizontalAlignment = HorizontalAlignment.Center,
            VerticalAlignment = VerticalAlignment.Center };
        indicator.Children.Add(halo); indicator.Children.Add(core);
        System.Windows.Automation.AutomationProperties.SetName(indicator, active ? "Agente trabajando" : "Agente inactivo");
        if (active && SystemParameters.ClientAreaAnimation)
        {
            var scale = new ScaleTransform(.72, .72); halo.RenderTransform = scale;
            var easing = new QuadraticEase { EasingMode = EasingMode.EaseOut };
            var grow = new DoubleAnimation(.72, 1.75, TimeSpan.FromMilliseconds(1050))
                { RepeatBehavior = RepeatBehavior.Forever, EasingFunction = easing };
            var fade = new DoubleAnimation(.46, 0, TimeSpan.FromMilliseconds(1050))
                { RepeatBehavior = RepeatBehavior.Forever, EasingFunction = easing };
            scale.BeginAnimation(ScaleTransform.ScaleXProperty, grow);
            scale.BeginAnimation(ScaleTransform.ScaleYProperty, grow.Clone());
            halo.BeginAnimation(OpacityProperty, fade);
        }
        return indicator;
    }

    static Border Badge(string label, bool model)
    {
        string foreground = "#C5C8D3", background = "#353741";
        if (model)
        {
            switch (label) {
                case "Luna": foreground = "#ACDEFF"; background = "#273B4B"; break;
                case "Terra": foreground = "#A4E4C6"; background = "#283E36"; break;
                case "Sol": foreground = "#F0D19C"; background = "#423A2A"; break;
                case "Astra": foreground = "#D5C3FF"; background = "#3B304E"; break;
            }
        }
        else
        {
            switch (label) {
                case "Ligero": foreground = "#BECADD"; background = "#313843"; break;
                case "Medio": foreground = "#ABDDDF"; background = "#293E42"; break;
                case "Alto": foreground = "#BCD0FF"; background = "#303952"; break;
                case "Muy alto": foreground = "#D9C5F6"; background = "#3C334D"; break;
                case "Máx.": foreground = "#F2CEB1"; background = "#48372F"; break;
                case "Ultra": foreground = "#F0BBD5"; background = "#493041"; break;
            }
        }
        var text = Txt(label, 12, Brush(foreground), FontWeights.SemiBold);
        text.TextAlignment = TextAlignment.Center; text.VerticalAlignment = VerticalAlignment.Center;
        text.LineHeight = 14; text.LineStackingStrategy = LineStackingStrategy.BlockLineHeight;
        return new Border { Background = Brush(background), CornerRadius = new CornerRadius(12), Height = 24, MinHeight = 24,
            VerticalAlignment = VerticalAlignment.Center, Padding = new Thickness(9, 0, 9, 0), Child = text,
            ToolTip = (model ? "Modelo: " : "Razonamiento: ") + label };
    }

    UIElement TaskRow(string id, Dictionary<string, object> row)
    {
        var grid = new Grid();
        grid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(56) });
        grid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
        grid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(100) });
        var agent = MakeAgentAvatar(id, row, true);
        agent.Slot.HorizontalAlignment = HorizontalAlignment.Left;
        Grid.SetColumn(agent.Slot, 0); grid.Children.Add(agent.Slot);
        string name = String(row, "name", id.Substring(0, Math.Min(8, id.Length)));
        var copy = new StackPanel { VerticalAlignment = VerticalAlignment.Center, Margin = new Thickness(0, 0, 14, 0) };
        var title = Txt(name, 13, Ink, FontWeights.SemiBold); title.ToolTip = name; copy.Children.Add(title);
        var status = Txt(Status(String(row, "status")), 12, Muted); status.Margin = new Thickness(0, 4, 0, 0); copy.Children.Add(status);
        Grid.SetColumn(copy, 1); grid.Children.Add(copy);
        var tags = new StackPanel { Width = 100, VerticalAlignment = VerticalAlignment.Center };
        tags.Children.Add(Badge(Model(Setting(row, "model", "Sin confirmar")), true));
        string effortLabel = Effort(Setting(row, "effort", ""));
        if (effortLabel != "")
        {
            var effort = Badge(effortLabel, false); effort.Margin = new Thickness(0, 4, 0, 0); tags.Children.Add(effort);
        }
        tags.ToolTip = String(row, "status") == "pending" ? "Selección pendiente de confirmar" : String(row, "confirmation", "Sin confirmar");
        Grid.SetColumn(tags, 2); grid.Children.Add(tags);
        var card = new Border { Margin = new Thickness(12, 3, 12, 3), Padding = new Thickness(8, 7, 8, 7),
            CornerRadius = new CornerRadius(16), Background = TransparentBrush, Cursor = Cursors.Hand,
            ToolTip = "Mostrar en Tarea destacada durante 1 minuto", Child = grid, Focusable = true };
        card.MouseEnter += delegate { card.Background = Panel2; };
        card.MouseLeave += delegate { card.Background = TransparentBrush; };
        card.MouseLeftButtonUp += delegate { SelectFeatured(id); };
        card.KeyDown += delegate(object sender, KeyEventArgs e) {
            if (e.Key == Key.Enter || e.Key == Key.Space) { SelectFeatured(id); e.Handled = true; }
        };
        return card;
    }

    UIElement Section(string text)
    {
        var label = Label(text); label.Margin = new Thickness(18, 14, 18, 5); return label;
    }

    UIElement EmptyRow(string text)
    {
        var block = Txt(text, 13, Muted); block.Margin = new Thickness(18, 10, 18, 10); return block;
    }

    static bool Active(string value) { return value == "active" || value == "inProgress" || value == "running" || value == "pending"; }
    static string Status(string value)
    {
        switch (value) { case "active": case "inProgress": case "running": return "Trabajando"; case "pending": return "Enviando";
            case "completed": case "idle": return "En espera"; case "waiting": return "Esperando tu respuesta"; case "error": case "failed": return "Error";
            case "interrupted": return "Interrumpida"; default: return "Estado sin confirmar"; }
    }
    static string Model(string value) { return value.Replace("gpt-5.6-", "").Replace("gpt-6-", "").Replace("gpt-", "").ToUpperInvariantFirst(); }
    static string Effort(string value)
    {
        switch (value) { case "low": return "Ligero"; case "medium": return "Medio"; case "high": return "Alto";
            case "xhigh": return "Muy alto"; case "max": return "Máx."; case "ultra": return "Ultra"; default: return ""; }
    }
    static Dictionary<string, object> Dict(object value) { return value as Dictionary<string, object> ?? new Dictionary<string, object>(); }
    static string String(Dictionary<string, object> value, string key, string fallback = "")
    { object found; return value != null && value.TryGetValue(key, out found) && found != null ? Convert.ToString(found) : fallback; }
    static int Int(Dictionary<string, object> value, string key) { int result; return Int32.TryParse(String(value, key), out result) ? result : 0; }
    static double Number(Dictionary<string, object> value, string key) { double result; return Double.TryParse(String(value, key), out result) ? result : 0; }

    void LoadUiState()
    {
        try
        {
            var state = Json.Deserialize<Dictionary<string, object>>(File.ReadAllText(UiStatePath));
            MonitorMode parsed; if (Enum.TryParse(String(state, "mode", "Compact"), out parsed)) mode = parsed;
            if (state.ContainsKey("topmost")) Topmost = Convert.ToBoolean(state["topmost"]);
            object heights;
            if (state.TryGetValue("panelHeights", out heights))
                foreach (var item in Dict(heights))
                {
                    double ratio = Convert.ToDouble(item.Value);
                    if (!Double.IsNaN(ratio) && !Double.IsInfinity(ratio) && ratio > 0 && ratio <= 1)
                        panelHeights[item.Key] = ratio;
                }
        }
        catch { mode = MonitorMode.Compact; Topmost = true; }
    }

    void SaveUiState()
    {
        if (preview) return;
        try
        {
            Directory.CreateDirectory(StateFolder);
            var temp = UiStatePath + ".tmp";
            File.WriteAllText(temp, Json.Serialize(new Dictionary<string, object> { { "mode", mode.ToString() }, { "topmost", Topmost }, { "panelHeights", panelHeights } }), new System.Text.UTF8Encoding(false));
            if (File.Exists(UiStatePath)) File.Replace(temp, UiStatePath, null); else File.Move(temp, UiStatePath);
        }
        catch { }
    }

    void OnClosing(object sender, System.ComponentModel.CancelEventArgs e)
    {
        if (!quitting && !preview) { e.Cancel = true; SwitchMode(MonitorMode.Hidden, true); return; }
        peekCloseTimer.Stop();
        foreach (var visual in agentAvatars.Values) SetAgentOrbit(visual, false);
        timer.Stop(); if (trayMenu != null) trayMenu.IsOpen = false; tray.Visible = false; tray.Dispose();
        Microsoft.Win32.SystemEvents.DisplaySettingsChanged -= DisplayChanged;
        SystemParameters.StaticPropertyChanged -= WorkAreaChanged;
    }

    public void Start()
    {
        SwitchMode(mode, false);
    }

    public void RenderPreviews()
    {
        Directory.CreateDirectory(StateFolder);
        Show();
        foreach (var item in new[] { new { Mode = MonitorMode.Compact, Name = "wpf-compact.png" }, new { Mode = MonitorMode.Expanded, Name = "wpf-expanded.png" } })
        {
            SwitchMode(item.Mode, false); UpdateLayout();
            Dispatcher.Invoke(delegate { }, DispatcherPriority.Render);
            SaveVisual(this, Path.Combine(StateFolder, item.Name), 1);
        }
        SelectMonitorTab(2); UpdateLayout();
        SaveVisual(this, Path.Combine(StateFolder, "wpf-statistics.png"), 1);
        quitting = true; Close();
    }
}

internal static class MonitorExtensions
{
    public static string ToUpperInvariantFirst(this string value)
    { return String.IsNullOrEmpty(value) ? value : Char.ToUpperInvariant(value[0]) + value.Substring(1); }
}

internal static class RouterMonitorProgram
{
    const string MutexName = "Local\\PersonalCodexRouterMonitorV6";
    const string RevealName = "Local\\PersonalCodexRouterMonitorV6Reveal";

    [STAThread]
    static int Main(string[] args)
    {
        bool review = args.Contains("--self-test");
        bool render = args.Contains("--render") || review, created;
        using (var mutex = new Mutex(true, MutexName, out created))
        {
            if (!created && !render)
            {
                if (!args.Contains("--tray"))
                    try { using (var signal = EventWaitHandle.OpenExisting(RevealName)) signal.Set(); } catch { }
                return 0;
            }
            var app = new Application { ShutdownMode = ShutdownMode.OnMainWindowClose };
            using (var reveal = new EventWaitHandle(false, EventResetMode.AutoReset, RevealName))
            {
                var monitor = new ModernRouterMonitor(render);
                app.MainWindow = monitor;
                if (review) return monitor.RunReviewChecks();
                if (render) { monitor.RenderPreviews(); return 0; }
                var thread = new Thread(new ThreadStart(delegate
                {
                    while (true) { try { reveal.WaitOne(); monitor.Dispatcher.BeginInvoke(new Action(monitor.Reveal)); } catch { return; } }
                })) { IsBackground = true };
                thread.Start();
                monitor.Start();
                app.Run();
            }
        }
        return 0;
    }
}
