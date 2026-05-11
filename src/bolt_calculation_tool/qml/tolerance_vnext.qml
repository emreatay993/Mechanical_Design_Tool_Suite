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
                ActionButton { text: "Save"; onClicked: backend.saveProject() }
                ActionButton { text: "Save As"; onClicked: backend.saveProjectAs() }
                ActionButton { text: "CSV"; onClicked: backend.exportCsv() }
                ActionButton { text: "PNG"; onClicked: backend.exportPng() }
                ActionButton { text: "PDF"; onClicked: backend.exportPdf() }
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
                                    property string jointId: modelData.id
                                    width: parent.width
                                    spacing: 4

                                    Rectangle {
                                        width: parent.width
                                        height: 36
                                        radius: 6
                                        color: modelData.selected ? "#e8f0ff" : "#f8fafc"
                                        border.color: modelData.selected ? "#8ab4ff" : "#e1e6ef"
                                        RowLayout {
                                            anchors.fill: parent
                                            anchors.leftMargin: 10
                                            anchors.rightMargin: 8
                                            Label {
                                                text: modelData.name
                                                Layout.fillWidth: true
                                                color: "#172033"
                                                font.bold: true
                                            }
                                        }
                                    }

                                    Repeater {
                                        model: modelData.sub_joints
                                        delegate: Button {
                                            width: parent.width
                                            height: 34
                                            text: "  " + modelData.name
                                            checkable: true
                                            checked: modelData.selected
                                            onClicked: backend.selectSubJoint(jointId, modelData.id)
                                            contentItem: Label {
                                                text: parent.text
                                                color: parent.checked ? "#0f4ca8" : "#344054"
                                                font.pixelSize: 12
                                                font.bold: parent.checked
                                                verticalAlignment: Text.AlignVCenter
                                            }
                                            background: Rectangle {
                                                radius: 6
                                                color: parent.checked ? "#dceaff" : "#ffffff"
                                                border.color: parent.checked ? "#75a7f8" : "#d8dee9"
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
                    Layout.preferredHeight: 178

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
                                text: "Linked flange values automatically feed the selected stackup path."
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
                                        width: 170
                                        height: 76
                                        radius: 8
                                        color: "#f8fafc"
                                        border.color: "#d8dee9"

                                        ColumnLayout {
                                            anchors.fill: parent
                                            anchors.margins: 8
                                            spacing: 4
                                            Label {
                                                text: modelData.name
                                                color: "#111827"
                                                font.bold: true
                                                font.pixelSize: 12
                                            }
                                            RowLayout {
                                                FieldBox {
                                                    id: flangeNominal
                                                    Layout.preferredWidth: 70
                                                    text: modelData.nominal
                                                    onEditingFinished: backend.updateFlange(modelData.id, text, flangeTolerance.text)
                                                }
                                                FieldBox {
                                                    id: flangeTolerance
                                                    Layout.preferredWidth: 70
                                                    text: modelData.tolerance
                                                    onEditingFinished: backend.updateFlange(modelData.id, flangeNominal.text, text)
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
                                Label { text: "Path item"; Layout.preferredWidth: 245; font.bold: true; color: "#334155" }
                                Label { text: "Source"; Layout.preferredWidth: 90; font.bold: true; color: "#334155" }
                                Label { text: "Thickness"; Layout.preferredWidth: 110; font.bold: true; color: "#334155" }
                                Label { text: "Tolerance"; Layout.preferredWidth: 110; font.bold: true; color: "#334155" }
                                Label { text: "Use"; Layout.preferredWidth: 50; font.bold: true; color: "#334155" }
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
                                        height: 52
                                        radius: 7
                                        color: modelData.locked ? "#fbfcff" : "#ffffff"
                                        border.color: modelData.locked ? "#d8dee9" : "#cfd6e3"

                                        RowLayout {
                                            anchors.fill: parent
                                            anchors.leftMargin: 10
                                            anchors.rightMargin: 10
                                            spacing: 10

                                            ColumnLayout {
                                                Layout.preferredWidth: 245
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
                                                Layout.preferredWidth: 90
                                                text: modelData.source_label
                                                color: "#64748b"
                                                font.pixelSize: 12
                                            }
                                            FieldBox {
                                                id: itemNominal
                                                Layout.preferredWidth: 110
                                                enabled: !modelData.locked
                                                text: modelData.nominal
                                                onEditingFinished: backend.updatePathItem(modelData.id, text, itemTolerance.text, includeBox.checked)
                                            }
                                            FieldBox {
                                                id: itemTolerance
                                                Layout.preferredWidth: 110
                                                enabled: !modelData.locked
                                                text: modelData.tolerance
                                                onEditingFinished: backend.updatePathItem(modelData.id, itemNominal.text, text, includeBox.checked)
                                            }
                                            CheckBox {
                                                id: includeBox
                                                Layout.preferredWidth: 50
                                                checked: modelData.include
                                                onToggled: backend.updatePathItem(modelData.id, itemNominal.text, itemTolerance.text, checked)
                                            }
                            Button {
                                Layout.preferredWidth: 34
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
                                                Label { text: modelData.sub_joint; Layout.preferredWidth: 100; color: "#111827"; font.bold: true }
                                                Label { text: "WC " + modelData.worst_case; Layout.preferredWidth: 86; color: "#334155" }
                                                Label { text: "RSS " + modelData.rss; Layout.preferredWidth: 86; color: "#334155" }
                                                Label { text: "1.5RSS " + modelData.one_point_five_rss; Layout.preferredWidth: 108; color: "#334155" }
                                                Label { text: "Top4 " + modelData.top_four; Layout.preferredWidth: 86; color: "#334155" }
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

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 14
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

                    SectionTitle { text: "Bolt and engagement" }
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

                    SectionTitle { text: "Thread checks" }
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

                    SectionTitle { text: "Optimization" }
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
                        Layout.fillHeight: true
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
                MutedText { text: "Qt Quick engineering workspace" }
            }
        }
    }
}
