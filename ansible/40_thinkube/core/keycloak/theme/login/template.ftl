<#macro registrationLayout bodyClass="" displayInfo=false displayMessage=true displayRequiredFields=false>
<!DOCTYPE html>
<html lang="en" class="${properties.kcHtmlClass!}">

<head>
    <meta charset="utf-8">
    <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
    <meta name="robots" content="noindex, nofollow">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">

    <#if properties.meta?has_content>
        <#list properties.meta?split(' ') as meta>
            <meta name="${meta?split('==')[0]}" content="${meta?split('==')[1]}"/>
        </#list>
    </#if>
    <title>${msg("loginTitle",(realm.displayName!''))}</title>
    <link rel="icon" href="${url.resourcesPath}/img/favicon.ico" />
    <#-- tkAssetVersion changes with the theme files, so browsers fetch new files after each deploy -->
    <#if properties.styles?has_content>
        <#list properties.styles?split(' ') as style>
            <link href="${url.resourcesPath}/${style}?v=${properties.tkAssetVersion}" rel="stylesheet" />
        </#list>
    </#if>
    <#if properties.scripts?has_content>
        <#list properties.scripts?split(' ') as script>
            <script src="${url.resourcesPath}/${script}?v=${properties.tkAssetVersion}" type="text/javascript"></script>
        </#list>
    </#if>
    <#if scripts??>
        <#list scripts as script>
            <script src="${script}" type="text/javascript"></script>
        </#list>
    </#if>
</head>

<body class="${properties.kcBodyClass!}">
    <#-- Colours are the thinkube-style tokens in hex: --primary, --brand-secondary, --background -->
    <canvas class="tk-bg" data-tk-terrain data-accent="#005474" data-warm="#ff6b36" data-background="#fdfaf3" aria-hidden="true"></canvas>
    <main class="tk-shell">
        <div class="tk-card">
            <img src="${url.resourcesPath}/img/logo.svg?v=${properties.tkAssetVersion}" alt="Thinkube" class="tk-logo" />

            <h1 id="kc-page-title"><#nested "header"></h1>

            <#if displayMessage && message?has_content && (message.type != 'warning' || !isAppInitiatedAction??)>
                <div class="alert alert-${message.type}" role="alert">
                    <span class="kc-feedback-text">${kcSanitize(message.summary)?no_esc}</span>
                </div>
            </#if>

            <#nested "form">

            <#if displayInfo>
                <div id="kc-info">
                    <#nested "info">
                </div>
            </#if>
        </div>
    </main>
</body>
</html>
</#macro>
