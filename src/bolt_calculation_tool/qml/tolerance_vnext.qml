import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ApplicationWindow {
    id: root
    visible: true
    width: 1480
    height: 920
    minimumWidth: 1360
    minimumHeight: 760
    title: "Tolerance Tool vNext"
    color: "#f4f6fb"
    font.family: "Segoe UI"
    font.pixelSize: 12
    readonly property int pathTableColumnSpacing: 10
    readonly property int pathItemColumnWidth: 225
    readonly property int pathSourceColumnWidth: 78
    readonly property int pathThicknessColumnWidth: 92
    readonly property int pathToleranceColumnWidth: 82
    readonly property int pathUseColumnWidth: 50
    readonly property int pathActionColumnWidth: 34

    function safeIndex(items, value) {
        if (!items || value === undefined)
            return -1
        for (var i = 0; i < items.length; i++) {
            if (String(items[i]) === String(value))
                return i
        }
        return -1
    }

    function objectIndex(items, key, value) {
        if (!items || value === undefined)
            return -1
        for (var i = 0; i < items.length; i++) {
            if (String(items[i][key]) === String(value))
                return i
        }
        return -1
    }

    function statusColor(status) {
        if (String(status).indexOf("Fail") >= 0)
            return "#c84747"
        if (String(status).indexOf("Warn") >= 0)
            return "#b7791f"
        if (String(status).indexOf("Incomplete") >= 0)
            return "#6b7280"
        return "#23845f"
    }

    component Card: Rectangle {
        color: "#ffffff"
        radius: 8
        border.color: "#d8dee9"
        border.width: 1
    }

    component SectionTitle: Label {
        color: "#172033"
        font.pixelSize: 14
        font.family: root.font.family
        font.bold: true
        Layout.fillWidth: true
    }

    component MutedText: Label {
        color: "#6b7280"
        font.pixelSize: 12
        font.family: root.font.family
        wrapMode: Text.WordWrap
        Layout.fillWidth: true
    }

    component ActionButton: Button {
        font.pixelSize: 12
        font.family: root.font.family
        leftPadding: 12
        rightPadding: 12
        topPadding: 6
        bottomPadding: 6
        contentItem: Text {
            text: parent.text
            color: parent.enabled ? "#1f3b63" : "#94a3b8"
            font: parent.font
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
        }
        background: Rectangle {
            radius: 7
            color: parent.down ? "#d7e7ff" : parent.hovered ? "#edf5ff" : "#ffffff"
            border.color: parent.activeFocus ? "#3b82f6" : "#cbd5e1"
        }
    }

    component FieldBox: TextField {
        selectByMouse: true
        font.pixelSize: 12
        font.family: root.font.family
        color: "#111827"
        selectedTextColor: "#ffffff"
        selectionColor: "#2563eb"
        padding: 8
        background: Rectangle {
            radius: 6
            color: parent.enabled ? "#ffffff" : "#f2f4f8"
            border.color: parent.activeFocus ? "#3b82f6" : "#cfd6e3"
        }
    }

    component SelectBox: ComboBox {
        font.pixelSize: 12
        font.family: root.font.family
        leftPadding: 10
        rightPadding: 28
        topPadding: 6
        bottomPadding: 6
        contentItem: Text {
            text: parent.displayText
            color: "#111827"
            font: parent.font
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
        }
        indicator: Text {
            text: "v"
            color: "#64748b"
            font.pixelSize: 12
            x: parent.width - width - 10
            y: parent.topPadding + (parent.availableHeight - height) / 2
        }
        background: Rectangle {
            radius: 7
            color: parent.down ? "#edf5ff" : "#ffffff"
            border.color: parent.activeFocus ? "#3b82f6" : "#cbd5e1"
        }
    }

    component Expander: ColumnLayout {
        id: section
        property string title: ""
        property bool expanded: true
        default property alias content: body.data
        Layout.fillWidth: true
        spacing: 6

        Button {
            Layout.fillWidth: true
            height: 34
            onClicked: section.expanded = !section.expanded
            contentItem: RowLayout {
                spacing: 8
                Text {
                    text: section.expanded ? "v" : ">"
                    color: "#475569"
                    font.pixelSize: 12
                    Layout.preferredWidth: 12
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
                Text {
                    text: section.title
                    color: "#172033"
                    font.pixelSize: 14
                    font.bold: true
                    Layout.fillWidth: true
                    verticalAlignment: Text.AlignVCenter
                }
            }
            background: Rectangle {
                radius: 7
                color: parent.down ? "#e8f0ff" : parent.hovered ? "#f4f8ff" : "#ffffff"
                border.color: "#d8dee9"
            }
        }

        ColumnLayout {
            id: body
            Layout.fillWidth: true
            visible: section.expanded
            spacing: 8
        }
    }

    component PathHeaderCell: Label {
        property int columnWidth: 80
        Layout.minimumWidth: columnWidth
        Layout.preferredWidth: columnWidth
        Layout.maximumWidth: columnWidth
        color: "#334155"
        font.bold: true
        elide: Text.ElideRight
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        Rectangle {
            Layout.fillWidth: true
            height: 70
            color: "#ffffff"
            border.color: "#d8dee9"
            border.width: 1

            RowLayout {
                anchors.fill: parent
                anchors.margins: 16
                spacing: 12

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 2
                    Label {
                        text: "Tolerance Tool vNext"
                        color: "#111827"
                        font.pixelSize: 20
                        font.bold: true
                    }
                    RowLayout {
                        spacing: 8
                        FieldBox {
                            id: titleField
                            Layout.preferredWidth: 320
                            text: backend.projectTitle
                            onEditingFinished: backend.setProjectTitle(text)
                        }
                        Label {
                            text: backend.unitSystem
                            color: "#2563eb"
                            font.pixelSize: 12
                            font.bold: true
                            padding: 6
                            background: Rectangle {
                                radius: 12
                                color: "#e8f0ff"
                            }
                        }
                        Label {
                            text: "Style"
                            color: "#475569"
                            font.pixelSize: 12
                            font.bold: true
                        }
                        SelectBox {
                            id: quickStyleBox
                            Layout.preferredWidth: 126
                            model: backend.availableQuickStyles
                            currentIndex: safeIndex(backend.availableQuickStyles, backend.quickStyle)
                            onActivated: backend.setQuickStyle(currentText)
                        }
                        SelectBox {
                            Layout.preferredWidth: 84
                            visible: backend.quickStyle === "Material"
                            model: backend.availableMaterialThemes
                            currentIndex: safeIndex(backend.availableMaterialThemes, backend.materialTheme)
                            onActivated: backend.setMaterialTheme(currentText)
                        }
                        Label {
                            text: backend.themeRestartRequired ? "Restart required" : "Active"
                            color: backend.themeRestartRequired ? "#b7791f" : "#23845f"
                            font.pixelSize: 12
                            font.bold: true
                        }
                        MutedText { text: backend.saveState }
                    }
                }

                ActionButton { text: "New"; onClicked: backend.newProject() }
                ActionButton { text: "Open"; onClicked: backend.openProject() }
                ActionButton { text: "Import"; onClicked: backend.importSpreadsheet() }
                ActionButton { text: "Save"; onClicked: backend.saveProject() }
                ActionButton { text: "Save As"; onClicked: backend.saveProjectAs() }
                Button {
                    id: exportButton
                    text: "Export"
                    font.pixelSize: 12
                    font.family: root.font.family
                    leftPadding: 12
                    rightPadding: 10
                    topPadding: 6
                    bottomPadding: 6
                    onClicked: exportMenu.open()

                    contentItem: RowLayout {
                        spacing: 6
                        Image {
                            Layout.preferredWidth: 15
                            Layout.preferredHeight: 15
                            source: "assets/icons/download.svg"
                            fillMode: Image.PreserveAspectFit
                        }
                        Text {
                            text: exportButton.text
                            color: exportButton.enabled ? "#1f3b63" : "#94a3b8"
                            font: exportButton.font
                            verticalAlignment: Text.AlignVCenter
                        }
                        Text {
                            text: "v"
                            color: "#64748b"
                            font.pixelSize: 11
                            verticalAlignment: Text.AlignVCenter
                        }
                    }
                    background: Rectangle {
                        radius: 7
                        color: exportButton.down ? "#d7e7ff" : exportButton.hovered ? "#edf5ff" : "#ffffff"
                        border.color: exportButton.activeFocus ? "#3b82f6" : "#cbd5e1"
                    }

                    Menu {
                        id: exportMenu
                        y: exportButton.height + 4
                        width: exportButton.width + 22
                        padding: 4

                        delegate: MenuItem {
                            id: exportMenuItem
                            implicitWidth: 138
                            implicitHeight: 34
                            leftPadding: 12
                            rightPadding: 12

                            contentItem: Text {
                                text: exportMenuItem.text
                                color: exportMenuItem.enabled ? "#1f2937" : "#94a3b8"
                                font.pixelSize: 12
                                font.family: root.font.family
                                verticalAlignment: Text.AlignVCenter
                                elide: Text.ElideRight
                            }
                            background: Rectangle {
                                radius: 5
                                color: exportMenuItem.highlighted ? "#edf5ff" : "#ffffff"
                            }
                        }

                        background: Rectangle {
                            radius: 7
                            color: "#ffffff"
                            border.color: "#cbd5e1"
                            border.width: 1
                        }

                        MenuItem { text: "Export CSV"; onTriggered: backend.exportCsv() }
                        MenuItem { text: "Export PNG"; onTriggered: backend.exportPng() }
                        MenuItem { text: "Export PDF"; onTriggered: backend.exportPdf() }
                    }
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 14
            Layout.margins: 14

            Card {
                Layout.preferredWidth: 270
                Layout.fillHeight: true

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 14
                    spacing: 10

                    SectionTitle { text: "Joints and sub-joints" }
                    MutedText {
                        text: "Select a sub-joint to edit its stackup path and bolt length."
                    }

                    ScrollView {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true

                        Column {
                            width: parent.width
                            spacing: 8
                            Repeater {
                                model: backend.joints
                                delegate: Column {
                                    id: navJoint
                                    property string jointId: modelData.id
                                    property string jointName: modelData.name
                                    property bool expanded: modelData.selected
                                    readonly property bool selectedParent: backend.selectedJoint.id === jointId
                                    width: parent.width
                                    spacing: 3

                                    Rectangle {
                                        width: parent.width
                                        height: 38
                                        radius: 6
                                        color: navJoint.selectedParent ? "#e8f0ff" : "#f8fafc"
                                        border.color: navJoint.selectedParent ? "#8ab4ff" : "#e1e6ef"
                                        RowLayout {
                                            anchors.fill: parent
                                            anchors.leftMargin: 8
                                            anchors.rightMargin: 8
                                            spacing: 8
                                            Label {
                                                text: navJoint.expanded || navJoint.selectedParent ? "v" : ">"
                                                Layout.preferredWidth: 16
                                                horizontalAlignment: Text.AlignHCenter
                                                verticalAlignment: Text.AlignVCenter
                                                color: navJoint.selectedParent ? "#0f4ca8" : "#667085"
                                                font.pixelSize: 12
                                                font.bold: true
                                            }
                                            Label {
                                                text: navJoint.jointName
                                                Layout.fillWidth: true
                                                color: navJoint.selectedParent ? "#0f4ca8" : "#172033"
                                                font.bold: true
                                            }
                                            Label {
                                                text: modelData.sub_joints.length
                                                Layout.preferredWidth: 24
                                                horizontalAlignment: Text.AlignHCenter
                                                verticalAlignment: Text.AlignVCenter
                                                color: "#667085"
                                                font.pixelSize: 11
                                            }
                                        }
                                        MouseArea {
                                            anchors.fill: parent
                                            cursorShape: Qt.PointingHandCursor
                                            onClicked: navJoint.expanded = !navJoint.expanded
                                        }
                                    }

                                    Item {
                                        width: parent.width
                                        visible: navJoint.expanded || navJoint.selectedParent
                                        height: visible ? childColumn.implicitHeight + 4 : 0
                                        clip: true

                                        Behavior on height {
                                            NumberAnimation { duration: 120; easing.type: Easing.OutCubic }
                                        }

                                        Rectangle {
                                            x: 16
                                            y: 2
                                            width: 1
                                            height: Math.max(0, childColumn.implicitHeight - 2)
                                            color: "#ccd6e3"
                                        }

                                        Column {
                                            id: childColumn
                                            width: parent.width
                                            spacing: 4

                                            Repeater {
                                                model: modelData.sub_joints
                                                delegate: Button {
                                                    readonly property bool childSelected: backend.selectedSubJoint.id === modelData.id
                                                    x: 24
                                                    width: parent.width - 24
                                                    height: 34
                                                    text: modelData.name
                                                    checkable: true
                                                    checked: childSelected
                                                    onClicked: backend.selectSubJoint(navJoint.jointId, modelData.id)
                                                    contentItem: Label {
                                                        text: parent.text
                                                        leftPadding: 12
                                                        color: parent.checked ? "#0f4ca8" : "#344054"
                                                        font.pixelSize: 12
                                                        font.bold: parent.checked
                                                        verticalAlignment: Text.AlignVCenter
                                                        elide: Text.ElideRight
                                                    }
                                                    background: Rectangle {
                                                        radius: 6
                                                        color: parent.checked ? "#dceaff" : "#ffffff"
                                                        border.color: parent.checked ? "#75a7f8" : "#d8dee9"
                                                        Rectangle {
                                                            width: 8
                                                            height: 1
                                                            x: -8
                                                            y: parent.height / 2
                                                            color: "#ccd6e3"
                                                        }
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        ActionButton {
                            Layout.fillWidth: true
                            text: "+ Joint"
                            onClicked: backend.addJoint()
                        }
                        ActionButton {
                            Layout.fillWidth: true
                            text: "+ Sub"
                            onClicked: backend.addSubJoint()
                        }
                    }
                    ActionButton {
                        Layout.fillWidth: true
                        text: "Duplicate selected sub-joint"
                        onClicked: backend.duplicateSelectedSubJoint()
                    }
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: 14

                Card {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 188

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 14
                        spacing: 10

                        RowLayout {
                            Layout.fillWidth: true
                            SectionTitle {
                                text: "Joint setup"
                                Layout.fillWidth: true
                            }
                            ActionButton { text: "+ Flange"; onClicked: backend.addFlange() }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 8
                            FieldBox {
                                id: jointNameField
                                Layout.preferredWidth: 180
                                text: backend.selectedJoint.name || ""
                                placeholderText: "Joint name"
                                onEditingFinished: backend.renameSelectedJoint(text, subNameField.text)
                            }
                            FieldBox {
                                id: subNameField
                                Layout.preferredWidth: 180
                                text: backend.selectedSubJoint.name || ""
                                placeholderText: "Sub-joint name"
                                onEditingFinished: backend.renameSelectedJoint(jointNameField.text, text)
                            }
                            MutedText {
                                Layout.fillWidth: true
                                text: "These thickness contributors are included in " + (backend.selectedSubJoint.name || "the selected sub-joint") + " stackup."
                            }
                        }

                        ScrollView {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            clip: true

                            Row {
                                spacing: 8
                                Repeater {
                                    model: backend.flanges
                                    delegate: Rectangle {
                                        width: 246
                                        height: 86
                                        radius: 8
                                        color: "#f8fafc"
                                        border.color: "#d8dee9"

                                        ColumnLayout {
                                            anchors.fill: parent
                                            anchors.margins: 8
                                            spacing: 4
                                            RowLayout {
                                                Layout.fillWidth: true
                                                Label {
                                                    text: modelData.name
                                                    color: "#111827"
                                                    font.bold: true
                                                    font.pixelSize: 12
                                                    Layout.fillWidth: true
                                                    elide: Text.ElideRight
                                                }
                                                Item {
                                                    Layout.preferredWidth: 26
                                                    Layout.preferredHeight: 24
                                                    ToolTip.text: "At least one flange is required."
                                                    ToolTip.visible: deleteFlangeHover.containsMouse && !modelData.can_delete

                                                    Button {
                                                        id: deleteFlangeButton
                                                        anchors.fill: parent
                                                        enabled: modelData.can_delete
                                                        onClicked: backend.deleteFlange(modelData.id)
                                                        contentItem: Item {
                                                            implicitWidth: 16
                                                            implicitHeight: 16
                                                            Image {
                                                                anchors.centerIn: parent
                                                                width: 15
                                                                height: 15
                                                                source: "assets/icons/trash-2.svg"
                                                                fillMode: Image.PreserveAspectFit
                                                                opacity: deleteFlangeButton.enabled ? 1.0 : 0.35
                                                            }
                                                        }
                                                        background: Rectangle {
                                                            radius: 6
                                                            color: parent.down ? "#fee2e2" : parent.hovered ? "#fff1f2" : "#f8fafc"
                                                            border.color: parent.enabled ? "#cbd5e1" : "#e2e8f0"
                                                        }
                                                    }
                                                    MouseArea {
                                                        id: deleteFlangeHover
                                                        anchors.fill: parent
                                                        acceptedButtons: Qt.NoButton
                                                        enabled: !modelData.can_delete
                                                        hoverEnabled: true
                                                    }
                                                }
                                            }
                                            RowLayout {
                                                FieldBox {
                                                    id: flangeNominal
                                                    Layout.preferredWidth: 70
                                                    text: modelData.nominal
                                                    onEditingFinished: backend.updateFlange(modelData.id, text, flangeTolMinus.text, flangeTolPlus.text)
                                                }
                                                FieldBox {
                                                    id: flangeTolMinus
                                                    Layout.preferredWidth: 70
                                                    text: modelData.tolerance_minus
                                                    placeholderText: "-Tol"
                                                    onEditingFinished: backend.updateFlange(modelData.id, flangeNominal.text, text, flangeTolPlus.text)
                                                }
                                                FieldBox {
                                                    id: flangeTolPlus
                                                    Layout.preferredWidth: 70
                                                    text: modelData.tolerance_plus
                                                    placeholderText: "+Tol"
                                                    onEditingFinished: backend.updateFlange(modelData.id, flangeNominal.text, flangeTolMinus.text, text)
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }

                Card {
                    Layout.fillWidth: true
                    Layout.fillHeight: true

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 14
                        spacing: 12

                        RowLayout {
                            Layout.fillWidth: true
                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 2
                                SectionTitle { text: "Stackup path: " + (backend.selectedSubJoint.name || "-") }
                                MutedText {
                                    text: "Flanges are linked from the joint setup. Add only extra brackets, washers, spacers, or custom items here."
                                }
                            }
                            ActionButton { text: "+ Custom"; onClicked: backend.addCustomPathItem() }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10

                            SelectBox {
                                id: hardwareCombo
                                Layout.preferredWidth: 260
                                model: backend.hardwareOptions
                                textRole: "display_name"
                                valueRole: "id"
                            }
                            ActionButton {
                                text: "Add catalog item"
                                onClicked: {
                                    if (hardwareCombo.currentIndex >= 0)
                                        backend.addCatalogPathItem(backend.hardwareOptions[hardwareCombo.currentIndex].id)
                                }
                            }
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            height: 34
                            color: "#eff4fb"
                            radius: 6
                            RowLayout {
                                anchors.fill: parent
                                anchors.leftMargin: 10
                                anchors.rightMargin: 10
                                spacing: root.pathTableColumnSpacing
                                PathHeaderCell { text: "Path item"; columnWidth: root.pathItemColumnWidth }
                                PathHeaderCell { text: "Source"; columnWidth: root.pathSourceColumnWidth }
                                PathHeaderCell { text: "Thickness"; columnWidth: root.pathThicknessColumnWidth }
                                PathHeaderCell { text: "-Tol"; columnWidth: root.pathToleranceColumnWidth }
                                PathHeaderCell { text: "+Tol"; columnWidth: root.pathToleranceColumnWidth }
                                PathHeaderCell { text: "Use"; columnWidth: root.pathUseColumnWidth }
                                Item {
                                    Layout.minimumWidth: root.pathActionColumnWidth
                                    Layout.preferredWidth: root.pathActionColumnWidth
                                    Layout.maximumWidth: root.pathActionColumnWidth
                                }
                                Item { Layout.fillWidth: true }
                            }
                        }

                        ScrollView {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            clip: true

                            Column {
                                width: parent.width
                                spacing: 8

                                Repeater {
                                    model: backend.pathItems
                                    delegate: Rectangle {
                                        width: parent.width
                                        height: 56
                                        radius: 7
                                        color: modelData.locked ? "#fbfcff" : "#ffffff"
                                        border.color: modelData.locked ? "#d8dee9" : "#cfd6e3"

                                        RowLayout {
                                            anchors.fill: parent
                                            anchors.leftMargin: 10
                                            anchors.rightMargin: 10
                                            spacing: root.pathTableColumnSpacing

                                            ColumnLayout {
                                                Layout.minimumWidth: root.pathItemColumnWidth
                                                Layout.preferredWidth: root.pathItemColumnWidth
                                                Layout.maximumWidth: root.pathItemColumnWidth
                                                spacing: 1
                                                Label {
                                                    text: modelData.name
                                                    color: "#111827"
                                                    font.pixelSize: 12
                                                    font.bold: true
                                                    elide: Text.ElideRight
                                                }
                                                MutedText { text: modelData.role }
                                            }
                                            Label {
                                                Layout.minimumWidth: root.pathSourceColumnWidth
                                                Layout.preferredWidth: root.pathSourceColumnWidth
                                                Layout.maximumWidth: root.pathSourceColumnWidth
                                                text: modelData.source_label
                                                color: "#64748b"
                                                font.pixelSize: 12
                                            }
                                            FieldBox {
                                                id: itemNominal
                                                Layout.minimumWidth: root.pathThicknessColumnWidth
                                                Layout.preferredWidth: root.pathThicknessColumnWidth
                                                Layout.maximumWidth: root.pathThicknessColumnWidth
                                                enabled: !modelData.locked
                                                text: modelData.nominal
                                                onEditingFinished: backend.updatePathItem(modelData.id, text, itemTolMinus.text, itemTolPlus.text, includeBox.checked)
                                            }
                                            FieldBox {
                                                id: itemTolMinus
                                                Layout.minimumWidth: root.pathToleranceColumnWidth
                                                Layout.preferredWidth: root.pathToleranceColumnWidth
                                                Layout.maximumWidth: root.pathToleranceColumnWidth
                                                enabled: !modelData.locked
                                                text: modelData.tolerance_minus
                                                onEditingFinished: backend.updatePathItem(modelData.id, itemNominal.text, text, itemTolPlus.text, includeBox.checked)
                                            }
                                            FieldBox {
                                                id: itemTolPlus
                                                Layout.minimumWidth: root.pathToleranceColumnWidth
                                                Layout.preferredWidth: root.pathToleranceColumnWidth
                                                Layout.maximumWidth: root.pathToleranceColumnWidth
                                                enabled: !modelData.locked
                                                text: modelData.tolerance_plus
                                                onEditingFinished: backend.updatePathItem(modelData.id, itemNominal.text, itemTolMinus.text, text, includeBox.checked)
                                            }
                                            CheckBox {
                                                id: includeBox
                                                Layout.minimumWidth: root.pathUseColumnWidth
                                                Layout.preferredWidth: root.pathUseColumnWidth
                                                Layout.maximumWidth: root.pathUseColumnWidth
                                                checked: modelData.include
                                                onToggled: backend.updatePathItem(modelData.id, itemNominal.text, itemTolMinus.text, itemTolPlus.text, checked)
                                            }
                                            Button {
                                                Layout.minimumWidth: root.pathActionColumnWidth
                                                Layout.preferredWidth: root.pathActionColumnWidth
                                                Layout.maximumWidth: root.pathActionColumnWidth
                                                enabled: !modelData.locked
                                                text: "x"
                                                onClicked: backend.removePathItem(modelData.id)
                                                contentItem: Text {
                                                    text: parent.text
                                                    color: parent.enabled ? "#475569" : "#cbd5e1"
                                                    horizontalAlignment: Text.AlignHCenter
                                                    verticalAlignment: Text.AlignVCenter
                                                }
                                                background: Rectangle {
                                                    radius: 6
                                                    color: parent.down ? "#fee2e2" : parent.hovered ? "#fff1f2" : "#f8fafc"
                                                    border.color: parent.enabled ? "#cbd5e1" : "#e2e8f0"
                                                }
                                            }
                                            Item { Layout.fillWidth: true }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }

                Card {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 166

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 14
                        spacing: 10

                        SectionTitle { text: "Project summaries" }
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 12
                            ScrollView {
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                clip: true
                                Column {
                                    width: parent.width
                                    spacing: 4
                                    Repeater {
                                        model: backend.summaryRows
                                        delegate: Rectangle {
                                            width: parent.width
                                            height: 30
                                            radius: 5
                                            color: "#f8fafc"
                                            RowLayout {
                                                anchors.fill: parent
                                                anchors.leftMargin: 8
                                                anchors.rightMargin: 8
                                                Label { text: modelData.sub_joint; Layout.preferredWidth: 92; color: "#111827"; font.bold: true }
                                                Label { text: "WC -" + modelData.worst_case_minus + "/+" + modelData.worst_case_plus; Layout.preferredWidth: 124; color: "#334155" }
                                                Label { text: "RSS -" + modelData.rss_minus + "/+" + modelData.rss_plus; Layout.preferredWidth: 124; color: "#334155" }
                                                Label { text: "MC " + modelData.mc_mean; Layout.preferredWidth: 84; color: "#334155" }
                                                Label { text: "Top4 " + modelData.top_four; Layout.preferredWidth: 78; color: "#334155" }
                                                Label { text: modelData.status; Layout.fillWidth: true; color: statusColor(modelData.status); font.bold: true }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }

            Card {
                Layout.preferredWidth: 360
                Layout.fillHeight: true

                ScrollView {
                    id: resultsScroll
                    anchors.fill: parent
                    anchors.margins: 14
                    clip: true
                    contentWidth: availableWidth

                    ColumnLayout {
                    width: resultsScroll.availableWidth
                    spacing: 12

                    SectionTitle { text: "Live results" }

                    Rectangle {
                        Layout.fillWidth: true
                        height: 42
                        radius: 8
                        color: "#f8fafc"
                        border.color: "#d8dee9"
                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 10
                            anchors.rightMargin: 10
                            Label { text: "Status"; Layout.fillWidth: true; color: "#64748b" }
                            Label {
                                text: backend.metrics.status || "-"
                                color: statusColor(text)
                                font.bold: true
                            }
                        }
                    }

                    GridLayout {
                        Layout.fillWidth: true
                        columns: 2
                        rowSpacing: 8
                        columnSpacing: 8

                        Repeater {
                            model: [
                                ["Nominal", backend.metrics.nominal || "-"],
                                ["Worst case dev.", backend.metrics.worst_case || "-"],
                                ["RSS", backend.metrics.rss || "-"],
                                ["1.5RSS", backend.metrics.one_point_five_rss || "-"],
                                ["Top 4 contributors", backend.metrics.top_four || "-"],
                                ["Protrusion", backend.metrics.protrusion || "-"]
                            ]
                            delegate: Rectangle {
                                Layout.fillWidth: true
                                Layout.preferredHeight: 58
                                radius: 8
                                color: "#f8fafc"
                                border.color: "#d8dee9"
                                ColumnLayout {
                                    anchors.fill: parent
                                    anchors.margins: 9
                                    spacing: 2
                                    MutedText { text: modelData[0] }
                                    Label {
                                        text: modelData[1]
                                        color: "#111827"
                                        font.pixelSize: 16
                                        font.bold: true
                                    }
                                }
                            }
                        }
                    }

                    MutedText {
                        Layout.fillWidth: true
                        text: "Top contributors: " + (backend.metrics.top_contributors || "-")
                    }

                    Expander {
                        title: "Monte Carlo"
                        expanded: backend.selectedSubJoint.monte_carlo_enabled || false
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 108
                        radius: 8
                        color: "#f8fafc"
                        border.color: "#d8dee9"
                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 9
                            spacing: 6
                            RowLayout {
                                Layout.fillWidth: true
                                CheckBox {
                                    id: monteCarloEnabled
                                    text: "Run"
                                    checked: backend.selectedSubJoint.monte_carlo_enabled || false
                                    onToggled: backend.updateMonteCarloSettings(checked, monteCarloSamples.text, monteCarloSeed.text)
                                }
                                FieldBox {
                                    id: monteCarloSamples
                                    Layout.preferredWidth: 82
                                    text: backend.selectedSubJoint.monte_carlo_sample_count || "10000"
                                    enabled: monteCarloEnabled.checked
                                    onEditingFinished: backend.updateMonteCarloSettings(monteCarloEnabled.checked, text, monteCarloSeed.text)
                                }
                                FieldBox {
                                    id: monteCarloSeed
                                    Layout.preferredWidth: 74
                                    text: backend.selectedSubJoint.monte_carlo_seed || "12345"
                                    enabled: monteCarloEnabled.checked
                                    onEditingFinished: backend.updateMonteCarloSettings(monteCarloEnabled.checked, monteCarloSamples.text, text)
                                }
                            }
                            MutedText {
                                text: monteCarloEnabled.checked
                                      ? "Mean " + backend.metrics.monte_carlo.mean + " | P0.135 " + backend.metrics.monte_carlo.p00135 + " | P99.865 " + backend.metrics.monte_carlo.p99865
                                      : "Disabled"
                            }
                            MutedText {
                                text: monteCarloEnabled.checked
                                      ? "Std " + backend.metrics.monte_carlo.std_deviation + " | min/max " + backend.metrics.monte_carlo.minimum + " / " + backend.metrics.monte_carlo.maximum
                                      : ""
                            }
                        }
                    }
                    }

                    Expander {
                        title: "Bolt and engagement"
                        expanded: true
                    SelectBox {
                        Layout.fillWidth: true
                        model: backend.boltSizes
                        currentIndex: safeIndex(backend.boltSizes, backend.selectedSubJoint.bolt_size)
                        onActivated: backend.setBoltSize(currentText)
                    }
                    SelectBox {
                        Layout.fillWidth: true
                        model: backend.boltTypes
                        currentIndex: safeIndex(backend.boltTypes, backend.selectedSubJoint.bolt_type)
                        onActivated: backend.setBoltType(currentText)
                    }
                    SelectBox {
                        Layout.fillWidth: true
                        model: backend.boltLengths
                        currentIndex: safeIndex(backend.boltLengths, backend.selectedSubJoint.bolt_length)
                        onActivated: backend.setBoltLength(currentText)
                    }
                    SelectBox {
                        Layout.fillWidth: true
                        model: ["nut", "insert"]
                        currentIndex: safeIndex(model, backend.selectedSubJoint.engagement_type)
                        onActivated: backend.setEngagementType(currentText)
                    }
                    SelectBox {
                        Layout.fillWidth: true
                        model: backend.engagementOptions
                        textRole: "display_name"
                        valueRole: "id"
                        currentIndex: objectIndex(backend.engagementOptions, "id", backend.selectedSubJoint.engagement_part_id)
                        onActivated: {
                            if (currentIndex >= 0)
                                backend.setEngagementPart(backend.engagementOptions[currentIndex].id)
                        }
                    }
                    }

                    Expander {
                        title: "Thread checks"
                        expanded: true
                    ScrollView {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 120
                        clip: true

                        Column {
                            width: parent.width
                            spacing: 6
                            Repeater {
                                model: backend.metrics.criteria || []
                                delegate: Rectangle {
                                    width: parent.width
                                    height: 34
                                    radius: 6
                                    color: "#f8fafc"
                                    RowLayout {
                                        anchors.fill: parent
                                        anchors.leftMargin: 8
                                        anchors.rightMargin: 8
                                        Label { text: modelData.name; Layout.fillWidth: true; color: "#111827"; font.bold: true }
                                        Label { text: modelData.actual + " / " + modelData.required; color: "#475569" }
                                        Label { text: modelData.status; color: statusColor(modelData.status); font.bold: true }
                                    }
                                }
                            }
                        }
                    }
                    }

                    Expander {
                        title: "Optimization"
                        expanded: false
                    RowLayout {
                        Layout.fillWidth: true
                        ActionButton {
                            Layout.fillWidth: true
                            text: "Apply recommended length"
                            onClicked: backend.applyRecommendedLength()
                        }
                    }
                    ScrollView {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 180
                        clip: true

                        Column {
                            width: parent.width
                            spacing: 6
                            Repeater {
                                model: backend.candidateRows
                                delegate: Rectangle {
                                    width: parent.width
                                    height: 58
                                    radius: 8
                                    color: modelData.recommended ? "#eaf6ef" : "#f8fafc"
                                    border.color: modelData.recommended ? "#74bd91" : "#d8dee9"

                                    ColumnLayout {
                                        anchors.fill: parent
                                        anchors.margins: 8
                                        spacing: 2
                                        RowLayout {
                                            Layout.fillWidth: true
                                            Label {
                                                text: modelData.recommended ? "Recommended " + modelData.length : modelData.length
                                                color: "#111827"
                                                font.bold: true
                                                Layout.fillWidth: true
                                            }
                                            Label {
                                                text: modelData.status
                                                color: statusColor(modelData.status)
                                                font.bold: true
                                            }
                                        }
                                        MutedText {
                                            text: modelData.message
                                            Layout.fillWidth: true
                                            elide: Text.ElideRight
                                        }
                                    }
                                }
                            }
                        }
                    }
                    }
                    }
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            height: 34
            color: "#ffffff"
            border.color: "#d8dee9"
            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 16
                anchors.rightMargin: 16
                Label {
                    text: backend.statusText
                    color: backend.statusText.indexOf("must") >= 0 || backend.statusText.indexOf("not") >= 0 ? "#c84747" : "#475569"
                    font.pixelSize: 12
                    Layout.fillWidth: true
                }
                MutedText { text: "Modern engineering workspace" }
            }
        }
    }
}
