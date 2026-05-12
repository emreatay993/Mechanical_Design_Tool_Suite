# EZtol Demo Media 1080p - Timestamped Transcript

- Pack directory: `C:\Users\emre_\PycharmProjects\Mechanical_Design_Tool_Suite\output\transcribe\eztol-demo-media-1080p`
- Video: `EZtol-Demo_Media_1080p.mp4`
- Caption cues: 295
- Transcript coverage: 00:00:00.000 to 00:32:32.000

Use this file for detailed questions about what is said at specific times in the video. The segment numbers match `EZtol-Demo_Media_1080p.segments.tsv`.

## Segment Transcript

### 00:00:00 - 00:01:00

- **001** `00:00:00.000 - 00:00:06.000` Basically, an assembly-level view, but with part-level details of how they're going to be controlled.
- **002** `00:00:06.000 - 00:00:11.000` Now, these particular parts have had GD&T applied. I will show both.
- **003** `00:00:11.000 - 00:00:27.000` I will do it in EZtol with linear dimensions and tolerances, and then I will modify those to show how the GD&T is defined within the tool for GPS, for the ISO standard.
- **004** `00:00:27.000 - 00:00:40.000` All right. So, to do this manually, we'll basically start at one side of the bushing or another, find the loop of parts and the loop of dimensions on those parts to get to the other side.
- **005** `00:00:40.000 - 00:00:46.000` So, the first thing that we see is the ID of the bushing is controlled with a runout of 0.1 to the OD.
- **006** `00:00:46.000 - 00:00:51.000` If I were to do this with a spreadsheet, it might look something very much like what you see in the lower left corner.
- **007** `00:00:51.000 - 00:01:06.000` You know, part name, description, the type of tolerance, and the effective amount of error it contributes to the vertical misalignment, recording both the nominal value, in this case 0 because they're coaxial, and plus or minus 5.
### 00:01:00 - 00:02:00

- **008** `00:01:06.000 - 00:01:13.000` Next, that bushing gets pressed into the hole that's held with a position of 0.15 relative to datum A.
- **009** `00:01:13.000 - 00:01:16.000` So, we put that in the spreadsheet.
- **010** `00:01:16.000 - 00:01:22.000` That allows the hole to move up and down by 0.075 millimeters, half the position tolerance.
- **011** `00:01:22.000 - 00:01:32.000` And then the support arm on the bushing is connected to a surface that's held per the ASME standards with the profile of 0.5 relative to datum A.
- **012** `00:01:32.000 - 00:01:35.000` In ISO, this would be position as well.
- **013** `00:01:35.000 - 00:01:45.000` But the point is that regardless of how it's specified, it too is allowed to move up and down plus or minus 0.25 millimeters relative to datum A.
- **014** `00:01:45.000 - 00:01:50.000` So, we have three contributors up one side, the same three back down the other side.
- **015** `00:01:50.000 - 00:02:01.000` And if we were to calculate this manually, we would see that the nominal dimensions are all aligned such that we are, in fact, seeing zero misalignment at nominal.
### 00:02:00 - 00:03:00

- **016** `00:02:01.000 - 00:02:04.000` This is good. This is what we want.
- **017** `00:02:04.000 - 00:02:12.000` And that the worst case variation is plus or minus 0.75, just the sum of all these individual variations.
- **018** `00:02:12.000 - 00:02:18.000` So, I'm going to hold this, have this sheet.
- **019** `00:02:18.000 - 00:02:25.000` Actually, I'm going to use this version with ethyl lines that we'll refer back to as I continue through the analysis in EZTOL.
- **020** `00:02:25.000 - 00:02:30.000` So, let's switch over to, I haven't even started. I thought I had opened it.
- **021** `00:02:30.000 - 00:02:35.000` I'll start EZTOL very quickly.
- **022** `00:02:35.000 - 00:02:41.000` Here's the main interface. Let me open a file.
- **023** `00:02:41.000 - 00:02:51.000` Now, EZTOL is a standalone application, but it pulls in geometry from many different CAD systems automatically.
- **024** `00:02:52.000 - 00:03:00.000` So, it supports Inventor, CATIA, NX, and JT if you've exported the amount of NX in that way.
### 00:03:00 - 00:04:00

- **025** `00:03:00.000 - 00:03:05.000` Creo, called Pro Engineer, and SOLIDWORKS, and some of the generic files.
- **026** `00:03:05.000 - 00:03:08.000` So, we can open a lot of different file formats.
- **027** `00:03:08.000 - 00:03:14.000` Today, I'm going to be working with a SOLIDWORKS version of the model, but I could choose any of them.
- **028** `00:03:14.000 - 00:03:20.000` So, I will filter on SOLIDWORKS, tell it I want the caster.
- **029** `00:03:20.000 - 00:03:27.000` During the import, and now what we're doing, what the tool is doing, it has its own 3D kernel, so it's importing the geometry.
- **030** `00:03:27.000 - 00:03:41.000` I actually have the option to either do a full conversion into the native format understood by our kernel, or actually create a copy that still references the source.
- **031** `00:03:41.000 - 00:03:50.000` Now, this is interesting because it allows any changes that occur in your designs to actually propagate through to the application,
- **032** `00:03:50.000 - 00:03:55.000` so that if you move features, make them thicker, move surfaces around,
- **033** `00:03:55.000 - 00:04:03.000` this reference option will allow you to reattach the analysis to that changed model in whatever source CAD system you're using.
### 00:04:00 - 00:05:00

- **034** `00:04:03.000 - 00:04:07.000` I'm going to go ahead and just convert these today.
- **035** `00:04:07.000 - 00:04:15.000` And, you'll see the caster wheel in the EZTool window.
- **036** `00:04:15.000 - 00:04:27.000` Now, for the purpose of this exercise, I'm going to go ahead and hide the wheel and the axle because we are not going to be using them.
- **037** `00:04:27.000 - 00:04:32.000` The main interface is you have a ribbon structure where we define stackups.
- **038** `00:04:32.000 - 00:04:38.000` We take snapshots of the stackup or of the high level view for inclusion in the report.
- **039** `00:04:38.000 - 00:04:45.000` We can add the, regenerate the report, and they have import and export for the data file.
- **040** `00:04:45.000 - 00:04:55.000` So, we actually can save the tolerance analysis in the converted geometry file information, or you can save it as a standalone as well.
- **041** `00:04:55.000 - 00:04:58.000` So, I'm going to go ahead and define the new stackup.
- **042** `00:04:58.000 - 00:05:04.000` Notice that when I do that, this little mini toolbar pops up to help guide me through the process.
### 00:05:00 - 00:06:00

- **043** `00:05:04.000 - 00:05:16.000` And, if I move my mouse to where you can see the tool tip that's tagging along with it, that travels with it, it's asking me to select a face edge or vertex.
- **044** `00:05:16.000 - 00:05:24.000` So, basically, what I'm doing is defining the measurement or the stackup endpoints, what it is we're going to study.
- **045** `00:05:25.000 - 00:05:28.000` We're going to study how aligned these two IDs of the bushings are.
- **046** `00:05:28.000 - 00:05:37.000` Now, because of the fact that I'm measuring between two cylinders, the tool is now expecting me to define a direction, and that could be an edge.
- **047** `00:05:37.000 - 00:05:38.000` It could be an axis.
- **048** `00:05:38.000 - 00:05:45.000` In this case, I'll use the top surface of the top plate, and the outward normal of that is going to be the direction of the stackup vertical.
- **049** `00:05:45.000 - 00:05:47.000` Now, it's asking me for an analysis plane.
- **050** `00:05:47.000 - 00:05:50.000` This is where it's going to place the annotations.
- **051** `00:05:50.000 - 00:05:57.000` And then, if I want to put the nominal value at a specific point, I just drag it.
- **052** `00:05:57.000 - 00:06:02.000` And I'm done with the definition of what it is I want to study.
### 00:06:00 - 00:07:00

- **053** `00:06:02.000 - 00:06:09.000` The next step is then to define what are the parts in the loop and how the parts connect together.
- **054** `00:06:09.000 - 00:06:11.000` What are the assembly constraints for those parts?
- **055** `00:06:11.000 - 00:06:13.000` So, I'll go ahead and do that.
- **056** `00:06:13.000 - 00:06:18.000` And now, notice it's a very quick selection of the objects.
- **057** `00:06:18.000 - 00:06:25.000` Once I've done that, the tooltip changes to, say, select a face, edge, or vertex from bushing 2 that mates with axle support 2.
- **058** `00:06:25.000 - 00:06:32.000` So, it's guiding me through the process of selecting different features on the parts for the assembly constraints.
- **059** `00:06:32.000 - 00:06:35.000` And notice that there's a lot of filtering going on.
- **060** `00:06:35.000 - 00:06:43.000` I can only select features from bushing 2, and I can only select features that actually are in the direction of the stackup.
- **061** `00:06:43.000 - 00:06:53.000` So, because of the choices we made the first time in that first part of the process, the selection here becomes very simple.
- **062** `00:06:53.000 - 00:06:56.000` It keeps track of what I've selected.
- **063** `00:06:56.000 - 00:07:01.000` Once I've selected all that I need, I select OK, and the stackup gets created.
### 00:07:00 - 00:08:00

- **064** `00:07:01.000 - 00:07:08.000` Now, of course, I can move these, make them be a little bit closer.
- **065** `00:07:08.000 - 00:07:15.000` And on the right-hand side, you'll see the stackup dimensions themselves.
- **066** `00:07:15.000 - 00:07:18.000` So, we showed the parts involved in the loop.
- **067** `00:07:18.000 - 00:07:27.000` For each part, it's automatically shown me the distance between the two surfaces that were defined as an assembly constraint.
- **068** `00:07:27.000 - 00:07:35.000` And this is interesting because this actually reflects the most effective dimensioning scheme for these parts for this analysis.
- **069** `00:07:35.000 - 00:07:41.000` Now, of course, we know we have multiple analysis competing requirements, but if considering nothing else,
- **070** `00:07:41.000 - 00:07:50.000` this is the most efficient dimensioning scheme for the parts to achieve alignment between these two bushings.
- **071** `00:07:50.000 - 00:07:56.000` Now, the tolerances that are assumed came out of the application options.
- **072** `00:07:56.000 - 00:08:03.000` So, here you would define typically a block tolerances so that the tool can actually help you identify where you need to be tighter.
### 00:08:00 - 00:09:00

- **073** `00:08:03.000 - 00:08:10.000` You have some other options here on the type of analysis you want to see by default and the types of quality metrics to use.
- **074** `00:08:10.000 - 00:08:14.000` I'll show you those when we look at different options.
- **075** `00:08:14.000 - 00:08:21.000` So, I said what I'm going to do initially is show what this stackup would look like using linear dimensions and stack tolerances.
- **076** `00:08:21.000 - 00:08:31.000` So, here we have the relationship, the coaxiality between the hole in the shaft of the bushing.
- **077** `00:08:31.000 - 00:08:35.000` And so, we said that that was in the spreadsheet in the calculation.
- **078** `00:08:35.000 - 00:08:39.000` We calculated that to be plus or minus 0.05.
- **079** `00:08:39.000 - 00:08:42.000` So, I'll just change it here.
- **080** `00:08:42.000 - 00:08:52.000` On the axial support, the distance between the hole and the face, we said, well, that is equivalent to plus or minus 0.075.
- **081** `00:08:52.000 - 00:08:54.000` So, I'll put that in here.
- **082** `00:08:54.000 - 00:09:02.000` Now, again, what I'm doing here is showing you what the workflow would be if we didn't have GPS on these prints.
### 00:09:00 - 00:10:00

- **083** `00:09:02.000 - 00:09:07.000` I'm showing you if we had linear dimensions and tolerances that look like this, this is how you would change it.
- **084** `00:09:07.000 - 00:09:12.000` I'll note that, you know, I can change the type of tolerance from symmetric plus minus limits.
- **085** `00:09:12.000 - 00:09:16.000` These are the three types for traditional dimensions.
- **086** `00:09:16.000 - 00:09:19.000` And, of course, I'll show you geometric in just a moment.
- **087** `00:09:19.000 - 00:09:26.000` Now, on the top plate, we notice that we actually are dimensioning from one side to the top and back down to the other side.
- **088** `00:09:26.000 - 00:09:31.000` But in EZTOL, it's just showing me the distance between the two planes on either side.
- **089** `00:09:31.000 - 00:09:39.000` Again, this is the most effective, most efficient control for the features that are important to the stack-up.
- **090** `00:09:39.000 - 00:09:43.000` But when you have something that's been done differently, of course, we need to accommodate that.
- **091** `00:09:43.000 - 00:09:49.000` In this case, we have an additional feature that's part of the loop that was not identified through that initial process.
- **092** `00:09:49.000 - 00:09:56.000` So, we just add the feature, tell the tool that this top surface is actually the reference for the others.
- **093** `00:09:56.000 - 00:10:01.000` That adds the feature within the stack-up definition.
### 00:10:00 - 00:11:00

- **094** `00:10:01.000 - 00:10:07.000` And, of course, now these are both plus or minus 0.025, I believe, 0.25.
- **095** `00:10:07.000 - 00:10:14.000` You can check very quickly, plus or minus 0.25.
- **096** `00:10:14.000 - 00:10:23.000` Now, when I get down to the other axle support and the, well, let's say here the bushing,
- **097** `00:10:23.000 - 00:10:28.000` notice that it's already received the tolerance from the one above it.
- **098** `00:10:28.000 - 00:10:36.000` So, we have the concept of a part that's used multiple times, and we don't require you to define a dimensioning scheme for that.
- **099** `00:10:36.000 - 00:10:45.000` Now, I've just noticed that on this, for some reason, I may have missed a selection.
- **100** `00:10:45.000 - 00:10:52.000` This should be, well, let's see, I don't think this is going to be, yeah.
- **101** `00:10:52.000 - 00:10:58.000` So, somehow I had missed the selection for the surface.
- **102** `00:10:58.000 - 00:10:59.000` It's not showing up.
- **103** `00:10:59.000 - 00:11:03.000` This is not, okay.
### 00:11:00 - 00:12:00

- **104** `00:11:03.000 - 00:11:07.000` I need to, I think I may have selected something inadvertently.
- **105** `00:11:07.000 - 00:11:11.000` Let's do this one again, just to make sure.
- **106** `00:11:11.000 - 00:11:18.000` What I'll do this time through, I've shown you the way to do it with the standard tolerances.
- **107** `00:11:18.000 - 00:11:22.000` This next time through, I'll go a little faster and show you how to apply the GPS,
- **108** `00:11:22.000 - 00:11:26.000` because I think what I've done is it's selected the same surface twice,
- **109** `00:11:26.000 - 00:11:32.000` rather than what I should have done is selected the two opposing surfaces.
- **110** `00:11:32.000 - 00:11:36.000` So, we'll try this one more time.
- **111** `00:11:36.000 - 00:11:55.000` Again, you'll get the idea of the speed now as I do this a little bit more without having to do as much explanation.
- **112** `00:11:55.000 - 00:12:00.000` I just want to confirm that, indeed, now, that I did make the right selection that time.
### 00:12:00 - 00:13:00

- **113** `00:12:00.000 - 00:12:05.000` I think I inadvertently selected the bottom surface of the top plate twice before.
- **114** `00:12:05.000 - 00:12:08.000` So, let's show the workflow now with GD&T.
- **115** `00:12:08.000 - 00:12:11.000` Here are the bushing on this particular drawing.
- **116** `00:12:11.000 - 00:12:15.000` The ID is held with a run out of 0.1 to the OD, which is datum A.
- **117** `00:12:15.000 - 00:12:18.000` So, I can call this datum A.
- **118** `00:12:18.000 - 00:12:20.000` Select geometric tolerance.
- **119** `00:12:20.000 - 00:12:26.000` Say the hole is controlled to datum A with a run out of 0.1.
- **120** `00:12:26.000 - 00:12:31.000` On the hole, it's held with a position of 0.15 to A, B, and C.
- **121** `00:12:31.000 - 00:12:34.000` So, again, the top of the surface is datum A.
- **122** `00:12:34.000 - 00:12:42.000` The hole is held with a position of 0.15 to datum A.
- **123** `00:12:42.000 - 00:12:46.000` Then, again, on the top plate, we have datum A as the top surface.
- **124** `00:12:46.000 - 00:12:49.000` So, I'll use the add feature.
- **125** `00:12:49.000 - 00:12:51.000` Rename that as A.
- **126** `00:12:51.000 - 00:13:03.000` Now, instead of using profile, which appears on the ESME print, I'll just show that in GPS, this would be a position.
### 00:13:00 - 00:14:00

- **127** `00:13:04.000 - 00:13:14.000` And, of course, we're showing the call out in the tree.
- **128** `00:13:24.000 - 00:13:29.000` So, now we have our tolerances defined in two different ways.
- **129** `00:13:33.000 - 00:13:40.000` Now, I'm going to go ahead and, oh, this is not 0.2, this is 0.5.
- **130** `00:13:46.000 - 00:13:49.000` Go ahead, and now we have the stack up.
- **131** `00:13:49.000 - 00:13:55.000` We're going to call this vertical coaxiality, so that we name it.
- **132** `00:13:55.000 - 00:13:59.000` The objective of the stack up is to be aligned within plus and minus 0.75.
- **133** `00:13:59.000 - 00:14:05.000` So, I'm going to go ahead and change my objective column to be plus or minus 0.750.
### 00:14:00 - 00:15:00

- **134** `00:14:08.000 - 00:14:14.000` And, now that I have the worst case results, I see that, indeed, it's meeting that.
- **135** `00:14:14.000 - 00:14:15.000` Everything is green.
- **136** `00:14:15.000 - 00:14:26.000` Now, had my objectives been something less than plus or minus 0.75, say 0.6, then, of course, we would show the results as extending beyond the requirements.
- **137** `00:14:26.000 - 00:14:28.000` So, the requirements are shown at the bottom.
- **138** `00:14:28.000 - 00:14:30.000` The results are shown at the top.
- **139** `00:14:30.000 - 00:14:34.000` And, at worst case, this would flag that we have an issue.
- **140** `00:14:34.000 - 00:14:42.000` In fact, if I go back to the summary table, which keeps a track of all my analyses, and also more about this in a minute,
- **141** `00:14:42.000 - 00:14:49.000` you'll see that there's a red indication to indicate that this is not meeting my requirements of plus or minus 0.6 at worst case.
- **142** `00:14:49.000 - 00:14:51.000` Well, of course, we have other options.
- **143** `00:14:51.000 - 00:14:53.000` We have an RSS option.
- **144** `00:14:53.000 - 00:14:57.000` So, this is a traditional root sum squares treatment.
- **145** `00:14:57.000 - 00:15:01.000` And, at this point, it's saying, well, that does meet it.
### 00:15:00 - 00:16:00

- **146** `00:15:01.000 - 00:15:03.000` It does fall within that range.
- **147** `00:15:03.000 - 00:15:09.000` And then, we can also offer statistical results with various quality metrics.
- **148** `00:15:09.000 - 00:15:18.000` So, let's say if I want to have a statistical result with a CP of 2, then I can show that.
- **149** `00:15:18.000 - 00:15:24.000` And, again, it's going to show me the results of the plot against the requirements.
- **150** `00:15:24.000 - 00:15:29.000` It's saying, well, I'm not achieving plus or minus 0.6 with a CPK of 2.
- **151** `00:15:29.000 - 00:15:37.000` I'm actually achieving, at this quality level, my current results as plus or minus 0.75.
- **152** `00:15:37.000 - 00:15:42.000` Or, alternatively, I'm achieving a plus or minus 0.6 with a quality level of 1.6.
- **153** `00:15:42.000 - 00:15:45.000` So, that's how to interpret this.
- **154** `00:15:45.000 - 00:15:52.000` Now, again, I can move my annotations to show the stack up on the report.
- **155** `00:15:52.000 - 00:15:55.000` But, I'm going to do this in a minute when I have more to show.
- **156** `00:15:55.000 - 00:16:04.000` One thing I do want to highlight before I jump to one that's been saved that has many different analyses defined is this message down here.
### 00:16:00 - 00:17:00

- **157** `00:16:04.000 - 00:16:09.000` It's saying, the calculated results are ignoring potentially significant 3D effects.
- **158** `00:16:09.000 - 00:16:11.000` Well, what does that mean?
- **159** `00:16:11.000 - 00:16:15.000` Well, EZTOL is a 1D analysis tool.
- **160** `00:16:15.000 - 00:16:23.000` And so, we're only looking at variation that occurs, translational variation that occurs in the direction that you've established for the stack up.
- **161** `00:16:23.000 - 00:16:31.000` However, because of the fact that we are actually using part level geometries to pull that information in,
- **162** `00:16:31.000 - 00:16:37.000` we have an understanding of the relationship between these parts and the relative size and kind of the offsets and things like that.
- **163** `00:16:37.000 - 00:16:46.000` So, we have implemented algorithms that look for common scenarios where a stack up may not be truly 1D.
- **164** `00:16:46.000 - 00:16:53.000` Because of a rotation or something else going on with the system, there may be more than error than what's predicted here.
- **165** `00:16:53.000 - 00:16:57.000` So, let me just go back to my worst case results.
- **166** `00:16:57.000 - 00:17:03.000` And at worst case, we did say that this was meeting plus or minus 0.75 initially.
### 00:17:00 - 00:18:00

- **167** `00:17:03.000 - 00:17:05.000` That's why everything is green.
- **168** `00:17:05.000 - 00:17:15.000` When I do this in CETOL, which is our full 3D analysis tool, here in this case, I've done this in SOLIDWORKS.
- **169** `00:17:15.000 - 00:17:19.000` We have a version of this that works in Creo and CATIA.
- **170** `00:17:19.000 - 00:17:23.000` And we actually have a version working with NX that's going to come out in a month or so.
- **171** `00:17:23.000 - 00:17:28.000` But the important thing is that the results of the worst case analysis.
- **172** `00:17:28.000 - 00:17:30.000` Let me turn this statistical off for a moment.
- **173** `00:17:30.000 - 00:17:40.000` The worst case analysis in CETOL would actually calculate a plus or minus 0.93 variation for this same analysis, for the same stack up.
- **174** `00:17:40.000 - 00:17:45.000` Now, the reason for that, we have visualization tools in CETOL to help you understand that.
- **175** `00:17:45.000 - 00:17:56.000` So, if I visualize the worst case as an example, what it's going to do, it's going to animate what is the position of these parts from one worst case extreme to the other.
- **176** `00:17:56.000 - 00:18:05.000` And when I show that animation, it's telling me that when something within the system rotates within its tolerant zone,
### 00:18:00 - 00:19:00

- **177** `00:18:05.000 - 00:18:13.000` it's causing me more misalignment between the two IDs of the bushings than if considering everything just translating.
- **178** `00:18:13.000 - 00:18:26.000` So this is what EZTOL was warning me about, that it detected that there's a good chance that rotations within the system are actually going to cause more variation than translations.
- **179** `00:18:26.000 - 00:18:34.000` And hence, you may want to go look at a more powerful tool if this analysis that you're running is critical.
- **180** `00:18:34.000 - 00:18:41.000` This is unique to our solution. No other 1D tolerant analysis solution, at least that we know of, is providing you this level of information.
- **181** `00:18:41.000 - 00:18:58.000` So not only is it giving you the results in various quality metrics, but it's basically indicating its own limitations to let you know that in situations where things may not be 1D,
- **182** `00:18:58.000 - 00:19:07.000` that if this is truly critical, you might want to go look at a more powerful solution that will take into account all 3D effects for this analysis.
### 00:19:00 - 00:20:00

- **183** `00:19:07.000 - 00:19:28.000` All right. So let me go ahead and close this window because I do want to show you one of the powerful things about the tool also is the fact that we don't just do one stack up.
- **184** `00:19:28.000 - 00:19:41.000` We manage multiple requirements on the assembly and we do that with a concept of a common dimensioning scheme.
- **185** `00:19:41.000 - 00:19:48.000` So when we have here, we have the model that has multiple different stack ups.
- **186** `00:19:48.000 - 00:19:51.000` You can see each one is shown here with a red nominal value indicating it.
- **187** `00:19:51.000 - 00:19:57.000` And in the table on the right hand side, you'll see a dashboard indicating everything that we've studied on this.
- **188** `00:19:57.000 - 00:20:03.000` So we look to see how flush the surfaces are on each side, the overall height.
### 00:20:00 - 00:21:00

- **189** `00:20:03.000 - 00:20:10.000` Make sure there's clearance above the wheel, the axial clearance around the wheel.
- **190** `00:20:10.000 - 00:20:16.000` That's actually to the side of the wheel, but it's the gap there to make things make sure things aren't going to compress.
- **191** `00:20:17.000 - 00:20:22.000` So multiple requirements, some green falling within tolerance standards, some red.
- **192** `00:20:22.000 - 00:20:27.000` Highlighting indicates there may be non 1D effects at play.
- **193** `00:20:27.000 - 00:20:30.000` Here's a roll up for each one of these.
- **194** `00:20:30.000 - 00:20:35.000` Again, you have the objective, the target quality, and this indicates the type of analysis.
- **195** `00:20:35.000 - 00:20:41.000` And if it's a statistical, the objective, the quality metric and the results against that.
- **196** `00:20:41.000 - 00:20:48.000` We also have a column on the right indicating the number of dimensions involved in the loop so that you can quickly go and see the complexity of these analyses.
- **197** `00:20:48.000 - 00:20:56.000` Am I treating something with 13 or more or 14 contributors as a as a worst case?
- **198** `00:20:56.000 - 00:20:59.000` Am I treating something with just two as a statistical?
- **199** `00:20:59.000 - 00:21:08.000` A very quick understanding of what is happening or the complexity of these analyses.
### 00:21:00 - 00:22:00

- **200** `00:21:08.000 - 00:21:15.000` Now, for any one of these, I can go in and drill down into the details of the stack up.
- **201** `00:21:15.000 - 00:21:21.000` So here is the the table. This is, again, similar to the table we create in the spreadsheet.
- **202** `00:21:21.000 - 00:21:26.000` One other thing, when you have multiple requirements, if you have a dimension.
- **203** `00:21:26.000 - 00:21:35.000` That is shared between multiple stack ups, you'll see an icon for it in this column so that I know very quickly if I change this tolerance,
- **204** `00:21:35.000 - 00:21:42.000` it's going to impact my overall height stack up and the clearance above wheel stack up.
- **205** `00:21:42.000 - 00:21:47.000` One other thing that I neglected to show when we were looking at the other one is if I wanted to see what's contributing,
- **206** `00:21:47.000 - 00:21:53.000` what's driving the variation in this particular result, we have a contributions tab.
- **207** `00:21:53.000 - 00:21:58.000` So when I go over to that, I can see, well, this one tolerance is, you know, this,
- **208** `00:21:58.000 - 00:22:04.000` this one profile is contributing almost 55 percent of the overall variation of the stack up.
### 00:22:00 - 00:23:00

- **209** `00:22:04.000 - 00:22:09.000` So, you know, what is driving it? So which tolerances make the most sense to reduce?
- **210** `00:22:09.000 - 00:22:14.000` Here, I'm going to what I'm going to do is going to take show a quick example of our snapshot.
- **211** `00:22:14.000 - 00:22:19.000` I'm going to do this one differently just to show what's going on.
- **212** `00:22:19.000 - 00:22:26.000` So in this case, I'm going to take this snapshot here. And what that snapshot will do is use this image in the report.
- **213** `00:22:26.000 - 00:22:30.000` I'll take at the upper level. The safe snapshot is this view.
- **214** `00:22:30.000 - 00:22:36.000` So I'll turn this around a bit, take that snapshot and let's generate the report.
- **215** `00:22:36.000 - 00:22:43.000` So I'm going to call this temp or test report. I'll just call it test.
- **216** `00:22:43.000 - 00:22:50.000` I shouldn't do that. I already have one there. It's a common name that I use.
- **217** `00:22:50.000 - 00:22:56.000` And as it runs the report, it's going and generating all those stack up loops to create the images.
- **218** `00:22:56.000 - 00:23:00.000` So there's the snapshot that we just took of the top level.
### 00:23:00 - 00:24:00

- **219** `00:23:00.000 - 00:23:07.000` And this report shows everything that's involved. And there's the dashboard again.
- **220** `00:23:07.000 - 00:23:15.000` A little bit wider. And for each one, we show the the looped up diagram that you save,
- **221** `00:23:15.000 - 00:23:20.000` the actual table of the tolerances, the results and the contributors.
- **222** `00:23:20.000 - 00:23:26.000` And on the left, I can jump to any one by selecting.
- **223** `00:23:26.000 - 00:23:32.000` The tab and then just going down, I forget the one we're looking at that I did at an angle.
- **224** `00:23:32.000 - 00:23:36.000` But it's in here somewhere. All right.
- **225** `00:23:36.000 - 00:23:40.000` At this point, I've this concludes the discussion.
- **226** `00:23:40.000 - 00:23:44.000` I think Daniel would like to say a few words, but before we turn it back over to him,
- **227** `00:23:44.000 - 00:23:52.000` I want to make sure that address any questions that you you may have.
- **228** `00:23:52.000 - 00:23:58.000` All right. So if you have any question, just.
- **229** `00:23:58.000 - 00:24:07.000` You can either do it in in the chat or unmute everybody and see who's got any question.
### 00:24:00 - 00:25:00

- **230** `00:24:07.000 - 00:24:13.000` I think it's from.
- **231** `00:24:13.000 - 00:24:18.000` Sorry, excuse me. I have my name is Eric from out to live. I have a question.
- **232** `00:24:18.000 - 00:24:27.000` Yeah, go ahead. When you did the calculation with a 3D effect, did you.
- **233** `00:24:27.000 - 00:24:34.000` Could you get the angular deviation in the results straight out from that?
- **234** `00:24:34.000 - 00:24:45.000` What the in in easy tall, which is the 3D analysis program, a separate application, I can look at the.
- **235** `00:24:45.000 - 00:24:54.000` If I look at the results, the top contributor for this is actually a rotation of the surface that the arm mounts to.
- **236** `00:24:54.000 - 00:24:58.000` And so what I'm the analysis is of a linear distance.
- **237** `00:24:58.000 - 00:25:05.000` But in this case, we have a surface on one part that when it is machined,
### 00:25:00 - 00:26:00

- **238** `00:25:05.000 - 00:25:15.000` created an angle within its tolerance zone is actually causing more vertical misalignment between this is exaggerated by 10.
- **239** `00:25:15.000 - 00:25:25.000` So causing more vertical misalignment than if that same surface translated through the tolerance zone.
- **240** `00:25:25.000 - 00:25:32.000` Yes. But could you get the angular deviation from the nominal?
- **241** `00:25:32.000 - 00:25:35.000` Oh, yes. If I. Right.
- **242** `00:25:35.000 - 00:25:49.000` If I defined this distance, not as a linear distance, but an angular, I could I could understand how what the angle angular error was between those two axes as well.
- **243** `00:25:50.000 - 00:25:56.000` But only in CETOL, easy tall does not calculate angles.
- **244** `00:25:56.000 - 00:25:59.000` OK, thank you. All right.
- **245** `00:25:59.000 - 00:26:08.000` We have a question from Elkin from Salem. Does the tool take thermal expansion of parts involved into consideration?
### 00:26:00 - 00:27:00

- **246** `00:26:08.000 - 00:26:12.000` No, it does not. It is something identified for the roadmap.
- **247** `00:26:12.000 - 00:26:19.000` But today there is no provision for doing that. OK.
- **248** `00:26:19.000 - 00:26:29.000` And the other who ask questions. All right.
- **249** `00:26:29.000 - 00:26:37.000` I'll just finish off if nobody has questions.
- **250** `00:26:37.000 - 00:26:42.000` I have one more question here from. Of course.
- **251** `00:26:42.000 - 00:26:52.000` Let's see. Is it impossible? Is it possible to import dimensioning straight from the model if it's a 3D dimension?
- **252** `00:26:52.000 - 00:26:58.000` Will that not today? Not today. What cat system do you use?
- **253** `00:26:59.000 - 00:27:02.000` Katia, not today. OK.
### 00:27:00 - 00:28:00

- **254** `00:27:02.000 - 00:27:16.000` This is our first release of easy tall and we are seeing the benefit of model based definition in CETOL that does have that capability because it's integrated directly within the CAD system.
- **255** `00:27:16.000 - 00:27:23.000` And it's something that we want to to definitely get to with this tool, but it's not not there right now.
- **256** `00:27:23.000 - 00:27:30.000` I will say if there's an inventor. User in the audience.
- **257** `00:27:30.000 - 00:27:36.000` That answer will for inventor users will change more quickly than some of the other systems.
- **258** `00:27:36.000 - 00:27:44.000` And part of the reason why is that if if you don't recognize it, we are using inventors kernel for this tool.
- **259** `00:27:44.000 - 00:27:49.000` So they they make a CAD system, but they also make the kernel available for users.
- **260** `00:27:49.000 - 00:27:59.000` And because of that, we actually have a version of this being released for inventor at the end of the month that will utilize that that PMI information.
- **261** `00:27:59.000 - 00:28:08.000` And of course, our intent is to go beyond that in the in the months, months ahead.
### 00:28:00 - 00:29:00

- **262** `00:28:08.000 - 00:28:16.000` So it's it's a roadmap item, but it's not there today. OK, thanks.
- **263** `00:28:16.000 - 00:28:24.000` All right. So I'll just finish off. Thanks for joining this webinar.
- **264** `00:28:24.000 - 00:28:31.000` I got another question here before. Can we calculate Sigma level?
- **265** `00:28:31.000 - 00:28:36.000` It does. So here's the roll up Sigma for all requirements. I think so.
- **266** `00:28:36.000 - 00:28:40.000` So that's. Oh, I'm sorry. Over to you again. There we go.
- **267** `00:28:40.000 - 00:28:44.000` So indeed. So we provide a roll up metric.
- **268** `00:28:44.000 - 00:28:48.000` So we look at the quality of all these and kind of roll it up into a single value. Here's the summary.
- **269** `00:28:48.000 - 00:29:00.000` Here's in this case, I'm using Sigma. So it said my my the target based upon all the objectives and the qualities requirement for the for the objectives is three point three six roll up.
### 00:29:00 - 00:30:00

- **270** `00:29:00.000 - 00:29:07.000` We're actually at a two point eight three. We can also calculate Sigma on an individual measurement level.
- **271** `00:29:08.000 - 00:29:12.000` Stack up level. So here's showing actual Sigma seven.
- **272** `00:29:12.000 - 00:29:21.000` Her objective is four and a half. OK.
- **273** `00:29:21.000 - 00:29:31.000` Great. Let's see if any other question comes in before I change to presenter again.
- **274** `00:29:31.000 - 00:29:40.000` It's good with questions, so that's just keep them coming if you have one.
- **275** `00:29:40.000 - 00:29:50.000` Either that or just contact me via email and we'll do some questions there. Right.
- **276** `00:29:51.000 - 00:30:01.000` Show my screen. So just if you're interested in easy to just contact me and we'll go over what options you have.
### 00:30:00 - 00:31:00

- **277** `00:30:01.000 - 00:30:08.000` Our next web demo. Oh, here's another question. Let's see.
- **278** `00:30:08.000 - 00:30:15.000` Do you see the questions to Stephen or did the four holes in the stack up?
- **279** `00:30:15.000 - 00:30:30.000` I expect I suspect that the reason you're asking about fit of patterns, it's possible to evaluate the fit of holes in a pattern, but you won't need all four of those.
- **280** `00:30:30.000 - 00:30:40.000` You can actually do it with two of them. And if you're assuming you're using the same tolerance on on the entire pattern, then through.
- **281** `00:30:40.000 - 00:30:46.000` Well, not symmetry, but through consistency, the others will will be there as well.
- **282** `00:30:46.000 - 00:30:59.000` And if if you'd like a kind of a follow up quick example of how to do that, we can we can get that to you.
- **283** `00:30:59.000 - 00:31:09.000` And if I misinterpreted your question, please, please feel free to set me back on course.
### 00:31:00 - 00:32:00

- **284** `00:31:09.000 - 00:31:14.000` OK, great. Great.
- **285** `00:31:14.000 - 00:31:23.000` So, yeah, we can do follow up sessions if you're interested. Just let us know and we'll take your questions separately as well.
- **286** `00:31:23.000 - 00:31:27.000` So I think you see my screen now.
- **287** `00:31:27.000 - 00:31:33.000` So next webinar is introduction to fame.
- **288** `00:31:33.000 - 00:31:38.000` So introduction to fame theory on the 21st of April.
- **289** `00:31:38.000 - 00:31:43.000` We have our GPS training from a building in September.
- **290** `00:31:43.000 - 00:31:49.000` We also have a CITO training. That's five days in November.
- **291** `00:31:49.000 - 00:31:58.000` Start of November, 16th of November. And then we have fame for constructors, fame for designers training in October.
- **292** `00:31:58.000 - 00:32:01.000` So thank you very much for joining us today.
### 00:32:00 - 00:33:00

- **293** `00:32:01.000 - 00:32:13.000` And as I said. Just let us know. Oh, not April. Sorry.
- **294** `00:32:13.000 - 00:32:18.000` That should be September. Thank you. All right.
- **295** `00:32:18.000 - 00:32:32.000` Thank you, everybody. Have a good day. Bye bye.
